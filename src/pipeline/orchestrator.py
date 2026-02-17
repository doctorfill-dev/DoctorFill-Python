"""
Pipeline Orchestrator - Coordinates the complete form filling process.

Combines:
1. Template loading (manual or auto)
2. Report text extraction and merging
3. RAG processing for question answering
4. XFA filling and PDF injection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config.settings import LOGS_DIR, LOG_JSON_DIR, LOG_XML_DIR, LOG_PDF_DIR
from ..config.form_registry import FormDescriptor
from ..core.template_manager import TemplateManager, FormTemplate
from ..core.type_converter import TypeConverter
from ..llm.provider import BaseLLMProvider, get_provider
from ..pdf.xfa import (
    extract_xfa_datasets,
    update_datasets,
    inject_datasets,
    discover_checkbox_paths,
    normalize_checkboxes,
)
from ..rag.processor import RAGProcessor, RAGConfig, RAGResponse
from .report_merger import merge_reports

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""
    success: bool
    output_pdf: Optional[Path] = None
    filled_fields: int = 0
    total_fields: int = 0
    responses: List[RAGResponse] = field(default_factory=list)
    error: Optional[str] = None
    log_files: Dict[str, Path] = field(default_factory=dict)


class PipelineOrchestrator:
    """
    Main pipeline orchestrator for form filling.

    Coordinates all components:
    1. Template management (manual or auto)
    2. Document processing with RAG
    3. XFA extraction, filling, and injection
    """

    def __init__(
        self,
        template_manager: Optional[TemplateManager] = None,
        provider: Optional[BaseLLMProvider] = None,
        rag_config: Optional[RAGConfig] = None,
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            template_manager: Template manager (creates default if None)
            provider: LLM provider (creates default if None)
            rag_config: RAG configuration (uses defaults if None)
        """
        self.template_manager = template_manager or TemplateManager()
        self.provider = provider or get_provider()
        self.rag_config = rag_config or RAGConfig()
        self.type_converter = TypeConverter()

    def process(
        self,
        form_id: str,
        report_pdfs: List[Union[str, Path]],
        output_path: Optional[Union[str, Path]] = None,
        save_logs: bool = True,
    ) -> PipelineResult:
        """
        Execute the complete form filling pipeline.

        Args:
            form_id: Form UUID or name
            report_pdfs: List of medical report PDF paths
            output_path: Optional output path for filled PDF
            save_logs: Whether to save intermediate logs

        Returns:
            PipelineResult with status and filled PDF path
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_files = {}

        try:
            # 1. Load template (manual or auto-generated)
            logger.info("Loading template for: %s", form_id)
            template = self.template_manager.get_template(form_id)
            descriptor = self.template_manager.get_descriptor(form_id)

            logger.info(
                "Template loaded: %s (manual=%s, fields=%d)",
                template.form_name,
                template.is_manual,
                len(template.fields)
            )

            # 2. Get questions for RAG
            questions = template.get_rag_questions()
            if not questions:
                return PipelineResult(
                    success=False,
                    error="No questions in template"
                )

            total_fields = len(questions)
            logger.info("Processing %d questions", total_fields)

            # 3. Extract and merge report text
            logger.info("Merging %d reports", len(report_pdfs))
            report_paths = [Path(p) for p in report_pdfs]
            merged_text = merge_reports(report_paths)

            if save_logs:
                merged_path = LOGS_DIR / f"merged_report_{timestamp}.txt"
                merged_path.write_text(merged_text, encoding="utf-8")
                log_files["merged_report"] = merged_path

            # 4. Initialize RAG processor
            logger.info("Initializing RAG pipeline")
            rag_processor = RAGProcessor(
                config=self.rag_config,
                provider=self.provider
            )

            # 5. Index documents
            num_chunks = rag_processor.index_documents([merged_text], progress=True)
            logger.info("Indexed %d chunks", num_chunks)

            # 6. Process questions through RAG
            logger.info("Processing questions through RAG")
            responses = rag_processor.process_questions(questions, progress=True)

            # 7. Map responses to XFA paths
            filled_values = self._map_responses_to_xfa(responses, template)

            if save_logs:
                import json
                responses_path = LOG_JSON_DIR / f"rag_responses_{timestamp}.json"
                responses_data = [r.to_dict() for r in responses]
                responses_path.write_text(
                    json.dumps(responses_data, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )
                log_files["responses"] = responses_path

            # 8. Extract XFA datasets
            logger.info("Extracting XFA datasets from form")
            datasets_xml = LOG_XML_DIR / f"datasets_extracted_{timestamp}.xml"
            extract_xfa_datasets(descriptor.form_pdf, datasets_xml)
            log_files["datasets_extracted"] = datasets_xml

            # 9. Discover and normalize checkboxes
            checkbox_paths = discover_checkbox_paths(datasets_xml)
            logger.info("Found %d checkbox fields", len(checkbox_paths))
            normalize_checkboxes(filled_values, checkbox_paths)

            # 10. Update datasets with filled values
            datasets_filled = LOG_XML_DIR / f"datasets_filled_{timestamp}.xml"
            update_datasets(
                datasets_xml,
                filled_values,
                datasets_filled,
                template.fields
            )
            log_files["datasets_filled"] = datasets_filled

            # 11. Generate output path if not specified
            if output_path is None:
                output_path = LOG_PDF_DIR / f"{template.form_name}_filled_{timestamp}.pdf"
            else:
                output_path = Path(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 12. Inject filled datasets into PDF
            logger.info("Injecting filled data into PDF")
            inject_datasets(descriptor.form_pdf, datasets_filled, output_path)
            log_files["output_pdf"] = output_path

            # Calculate filled fields
            filled_count = sum(1 for r in responses if r.value is not None)

            logger.info(
                "Pipeline complete: %d/%d fields filled, output: %s",
                filled_count, total_fields, output_path
            )

            return PipelineResult(
                success=True,
                output_pdf=output_path,
                filled_fields=filled_count,
                total_fields=total_fields,
                responses=responses,
                log_files=log_files
            )

        except Exception as e:
            logger.error("Pipeline failed: %s", e, exc_info=True)
            return PipelineResult(
                success=False,
                error=str(e),
                log_files=log_files
            )

    def _map_responses_to_xfa(
        self,
        responses: List[RAGResponse],
        template: FormTemplate
    ) -> Dict[str, Any]:
        """
        Map RAG responses to XFA paths with type conversion.

        Args:
            responses: RAG responses
            template: Form template

        Returns:
            Dict of XFA path -> value
        """
        values = {}

        for response in responses:
            if response.value is None:
                continue

            # Get XFA path for this field
            xfa_path = template.get_xfa_path(response.id)
            if not xfa_path:
                logger.warning("No XFA path for field: %s", response.id)
                continue

            # Get field type and convert
            field_type = template.get_field_type(response.id)
            converted_value = self.type_converter.convert(
                response.value,
                field_type,
                response.id
            )

            values[xfa_path] = converted_value

        logger.info("Mapped %d values to XFA paths", len(values))
        return values
