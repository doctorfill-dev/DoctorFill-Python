# patient 1
- nom : `page1 > patientS1Address > lastName`
- prénom : `page1 > patientS1Address > firstName`
- date de naissance : `page1 > patientS1Address > birthDate`
- rue : `page1 > patientS1Address > street`
- lieu : `page1 > patientS1Address > city`
- np : `page1 > patientS1Address > zip` 
- téléphone : `page1 > patientS1Address > phone`
- mail : `page1 > patientS1Address > email`
- n° avs : `page1 > patientS1Address > ssn`
- sexe : `page1 > patientS1Address > sex`

# destinataire 2
- gln : `page1 > providerS1Address > ean`
- rcc : `page1 > providerS1Address > zsr`
- mail : `page1 > providerS1Address > email`
- adresse (max 50 mots) : `page1 > providerS1Address > blockAddress`

# assurance 3
- adresse (max 30 mots) : `insuranceS1Address > blockAddress`
- GLN : `insuranceS1Address > ean`

# lois/case 4 
- motifs du traitement : `page1 > treatmentReason` : liste : maladie, accident, grossesse, prévention, infirmité congénitale, inconnue
- loi : `page1 > lawS1Struct > type` : liste : kvg, vvg, uvg, ivg, mvg
- numéro d'assuré : `page1 > lawS1Struct > insuredID`
- numéro d'accident : `page1 > lawS1Struct > caseID`
- date d'accident : `page1 > lawS1Struct > caseDate`

# date de l'examen 5
- urgent (ON/OFF) : `page1 > appointmentUrgency`
- patient se présente (booléen) : `page1 > appointmentType` = 0
- prendre rendez-vous dès le (date jj.mm.aaaa) : `page1 > appointmentType` = 1 + `page1 > appointmentAfterDate`
- rendez-vous pris le (date jj.mm.aaaa) : `page1 > appointmentType` = 2 + `page1 > appointmentFixedDate`

# examen demandé 6
- ECG (ON/OFF) : `page1 > ecgExam`
- ECG 72h (ON/OFF) : `page1 > ecg72hExam`
- Contrôle de tension artérielle 24h (ON/OFF) : `page1 > bp24hExam`
- Ergométrie de stress (ON/OFF) : `page1 > stressErgometryExam`
- Echocardiographie de stress (ON/OFF) : `page1 > stressEchocardiographyExam`
- ECG 24h (ON/OFF) : `page1 > ecg24hExam`
- ECG à long terme / Holter ECG (ON/OFF) : `page1 > ecgHolterExam`
- Echocardiographie (ON/OFF) : `page1 > echocardiographyExam`
- Contrôle du stimulateur cardiaque (ON/OFF) : `page1 > pacemakerControl`
- Autre (préciser max 50 mots) (ON/OFF) : `page1 > otherConsultation` et `page1 > consultationDescription`

# indication / question 7
- champ libre (max 700 mots) : `page1 > anamnesis` : si pas assez de place, ajouter sous `remark`

# médecin spécialiste 8 
- texte libre (max 50 mots) : `page1 > providerS1Address > blockAddress`
- mail : `page1 > providerS1Address > email`
- GLN : `page1 > providerS1Address > ean`
- téléphone : `page1 > providerS1Address > phone`
- RCC : `page1 > providerS1Address > zsr`

# médecin de famille 9
- texte libre (max 50 mots) : `page1 > gpS1Address > input`
- mail : `page1 > gpS1Address > email`
- GLN : `page1 > gpS1Address > ean`
- téléphone : `page1 > gpS1Address > phone`
- RCC : `page1 > gpS1Address > zsr`


# Remarques 10
- texte libre (max 900 mots) : `page2 > remark` : lier à `anamnesis`

