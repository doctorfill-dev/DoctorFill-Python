# page 1 (seite 1)
Spécialité : pour insérer le canton il faut insérer une ligne. 
Par défaut le parse du XML : 
```xml
<treatmentS1Struct>
    <treatmentCanton>
        <value/>
    </treatmentCanton>
    <input></input>
</treatmentS1Struct>
```

Pour insérer le canton il faut insérer une ligne dans le XML. Par exemple pour Fribourg :
```xml
<treatmentS1Struct>
    <treatmentCanton>
        <value/>
    </treatmentCanton>
    <input></input>
    <treatmentCanton>FR</treatmentCanton>
</treatmentS1Struct>
```

- canton : `treatmentCanton`

_A voir encore comment remplir cela dynamiquement_

Le reste est rempli automatiquement par le PDF. 

# page 2 (seite 2)

## default
```xml
<Seite2>
    <untertitel_2checkbox xfa:dataNode="dataGroup"/>
    <patientS1Address>
        <firstName></firstName>
        <lastName></lastName>
        <birthDate></birthDate>
        <ssn></ssn>
        <input></input>
        <street></street>
        <city></city>
        <zip></zip>
        <sex>
            <value/>
        </sex>
        <phone></phone>
    </patientS1Address>
    <contactPhoneByPhysician></contactPhoneByPhysician>
    <header xfa:dataNode="dataGroup"/>
    <statusOFProceedings></statusOFProceedings>
    <contactTimeByPhysician></contactTimeByPhysician>
    <contactPhoneByIV></contactPhoneByIV>
    <contactTimeByIV></contactTimeByIV>
</Seite2>
```

## filled
```xml
            <Seite2>
                <untertitel_2checkbox xfa:dataNode="dataGroup"/>
                <patientS1Address>
                    <firstName>Prénom</firstName>
                    <lastName>Nom</lastName>
                    <birthDate>DateNaissance</birthDate>
                    <ssn>NumeroAVS</ssn>
                    <input/>
                    <street>Rue, numéro</street>
                    <city>Lieu</city>
                    <zip>NPA</zip>
                    <sex>M</sex>
                    <phone>NumeroTelephone</phone>
                </patientS1Address>
                <contactPhoneByPhysician>NoTel1</contactPhoneByPhysician>
                <header xfa:dataNode="dataGroup"/>
                <statusOFProceedings>Stade de la procédure</statusOFProceedings>
                <contactTimeByPhysician>CrenHoraire1</contactTimeByPhysician>
                <contactPhoneByIV>NoTel2</contactPhoneByIV>
                <contactTimeByIV>CrenHoraire2</contactTimeByIV>
            </Seite2>
```

# page 3 (seite 3)
```xml
<Seite3>
    <rotertitel_untertitel_einfachfeld>
        <titel_untertitel xfa:dataNode="dataGroup"/>
    </rotertitel_untertitel_einfachfeld>
    <tab1>
        <treatmentFrequency></treatmentFrequency>
    </tab1>
    <rotertitel_untertitel_einfachfeld_2erBlock>
        <Befund xfa:dataNode="dataGroup"/>
        <untertitel_2erblock>
            <fromDate></fromDate>
            <toDate></toDate>
            <lastControlDate></lastControlDate>
        </untertitel_2erblock>
    </rotertitel_untertitel_einfachfeld_2erBlock>
    <untertitel-1zeilen_einfachfeld1>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <controlsBeforeBy></controlsBeforeBy>
        </tab1>
    </untertitel-1zeilen_einfachfeld1>
    <untertitel-1zeilen_einfachfeld2>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <controlsAfterBy></controlsAfterBy>
        </tab1>
    </untertitel-1zeilen_einfachfeld2>
    <mehrfachfeld>
        <otherPhysicians></otherPhysicians>
    </mehrfachfeld>
    <header xfa:dataNode="dataGroup"/>
    <untertitel_4erblock xfa:dataNode="dataGroup"/>
    <AUF01>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF01>
    <AUF02>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF02>
    <AUF03>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF03>
    <AUF04>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF04>
    <AUF05>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF05>
    <AUF06>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF06>
    <AUF07>
        <percent></percent>
        <fromDate></fromDate>
        <toDate></toDate>
    </AUF07>
    <jobDescription></jobDescription>
    <anamnesis></anamnesis>
</Seite3>
```

```xml
<Seite3>
    <rotertitel_untertitel_einfachfeld>
        <titel_untertitel xfa:dataNode="dataGroup"/>
    </rotertitel_untertitel_einfachfeld>
    <tab1>
        <treatmentFrequency>1.2 - p1</treatmentFrequency>
    </tab1>
    <rotertitel_untertitel_einfachfeld_2erBlock>
        <Befund xfa:dataNode="dataGroup"/>
        <untertitel_2erblock>
            <fromDate>1.1 - p1</fromDate>
            <toDate>1.1 - p2</toDate>
            <lastControlDate>1.1 - p3</lastControlDate>
        </untertitel_2erblock>
    </rotertitel_untertitel_einfachfeld_2erBlock>
    <untertitel-1zeilen_einfachfeld1>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <controlsBeforeBy>1.1 - p4</controlsBeforeBy>
        </tab1>
    </untertitel-1zeilen_einfachfeld1>
    <untertitel-1zeilen_einfachfeld2>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <controlsAfterBy>1.1 - p5</controlsAfterBy>
        </tab1>
    </untertitel-1zeilen_einfachfeld2>
    <mehrfachfeld>
        <otherPhysicians>1.4</otherPhysicians>
    </mehrfachfeld>
    <header xfa:dataNode="dataGroup"/>
    <untertitel_4erblock xfa:dataNode="dataGroup"/>
    <AUF01>
        <percent>1.31000000</percent>
        <fromDate>1.31-p1</fromDate>
        <toDate>1.31-p2</toDate>
    </AUF01>
    <AUF02>
        <percent>1.32000000</percent>
        <fromDate>1.32-p1</fromDate>
        <toDate>1.32-p2</toDate>
    </AUF02>
    <AUF03>
        <percent>1.33000000</percent>
        <fromDate>1.33-p1</fromDate>
        <toDate>1.33-p2</toDate>
    </AUF03>
    <AUF04>
        <percent>1.34000000</percent>
        <fromDate>1.34-p1</fromDate>
        <toDate>1.34-p2</toDate>
    </AUF04>
    <AUF05>
        <percent>1.35000000</percent>
        <fromDate>1.35-p1</fromDate>
        <toDate>1.35-p2</toDate>
    </AUF05>
    <AUF06>
        <percent>1.36000000</percent>
        <fromDate>1.36-p1</fromDate>
        <toDate>1.36-p2</toDate>
    </AUF06>
    <AUF07>
        <percent>1.37000000</percent>
        <fromDate>1.37-p1</fromDate>
        <toDate>1.37-p2</toDate>
    </AUF07>
    <jobDescription>1.3 - p1</jobDescription>
    <anamnesis>2.1</anamnesis>
</Seite3>
```

# page 4 (seite 4)
```xml
<Seite4>
    <untertitel-1zeilen_mehrfachfeld0>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <symptoms></symptoms>
        </tab1>
    </untertitel-1zeilen_mehrfachfeld0>
    <tab1>
        <diagnosisAffectingITW></diagnosisAffectingITW>
    </tab1>
    <rotertitel_untertitel_einfachfeld1>
        <titel_untertitel xfa:dataNode="dataGroup"/>
        <mehrfachfeld>
            <findings></findings>
        </mehrfachfeld>
    </rotertitel_untertitel_einfachfeld1>
    <tab1>
        <medication></medication>
    </tab1>
    <Titel_Untertitel xfa:dataNode="dataGroup"/>
    <header xfa:dataNode="dataGroup"/>
</Seite4>
```

```xml
<Seite4>
    <untertitel-1zeilen_mehrfachfeld0>
        <Titel_Untertitel xfa:dataNode="dataGroup"/>
        <tab1>
            <symptoms>2.2</symptoms>
        </tab1>
    </untertitel-1zeilen_mehrfachfeld0>
    <tab1>
        <diagnosisAffectingITW>2.5</diagnosisAffectingITW>
    </tab1>
    <rotertitel_untertitel_einfachfeld1>
        <titel_untertitel xfa:dataNode="dataGroup"/>
        <mehrfachfeld>
            <findings>2.4</findings>
        </mehrfachfeld>
    </rotertitel_untertitel_einfachfeld1>
    <tab1>
        <medication>2.3</medication>
    </tab1>
    <Titel_Untertitel xfa:dataNode="dataGroup"/>
    <header xfa:dataNode="dataGroup"/>
</Seite4>
```

# page 5 (seite 5)
```xml
<Seite5>
    <rotertitel_untertitel_einfachfeld>
        <prognosisForITW></prognosisForITW>
    </rotertitel_untertitel_einfachfeld>
    <rotertitel_untertitel_einfachfeld4>
        <titel_untertitel xfa:dataNode="dataGroup"/>
    </rotertitel_untertitel_einfachfeld4>
    <header xfa:dataNode="dataGroup"/>
    <diagnosisNotAffectingITW></diagnosisNotAffectingITW>
    <treatmentPlan></treatmentPlan>
</Seite5>
```

```xml
<Seite5>
    <rotertitel_untertitel_einfachfeld>
        <prognosisForITW>2.7</prognosisForITW>
    </rotertitel_untertitel_einfachfeld>
    <rotertitel_untertitel_einfachfeld4>
        <titel_untertitel xfa:dataNode="dataGroup"/>
    </rotertitel_untertitel_einfachfeld4>
    <header xfa:dataNode="dataGroup"/>
    <diagnosisNotAffectingITW>2.6</diagnosisNotAffectingITW>
    <treatmentPlan>2.8</treatmentPlan>
</Seite5>
```

# page 6 (seite 6)
```xml
<Seite6>
    <informationForActivity></informationForActivity>
    <header xfa:dataNode="dataGroup"/>
    <workingActivity></workingActivity>
    <q31Unknown>0</q31Unknown>
    <q32None>0</q32None>
    <requirementsForActivity></requirementsForActivity>
    <q33None>0</q33None>
    <q34None>0</q34None>
    <functionalRestrictions></functionalRestrictions>
    <q35Unknown>0</q35Unknown>
    <functionalRestrictions></functionalRestrictions>
    <q36Unknown>0</q36Unknown>
    <doubtsForDrivingAbility></doubtsForDrivingAbility>
</Seite6>
```

```xml
<Seite6>
    <informationForActivity>3.2 - avec check box "aucune information"</informationForActivity>
    <header xfa:dataNode="dataGroup"/>
    <workingActivity>3.1 - avec check box pour "Je ne suis pas en mesure de répondre de cette question</workingActivity>
    <q31Unknown>1</q31Unknown>
    <q32None>1</q32None>
    <requirementsForActivity>3.3 - avec check box "je ne suis pas en mesure de répondre à cette question au cas où vous disposez ..."</requirementsForActivity>
    <q33None>1</q33None>
    <q34None>1</q34None>
    <functionalRestrictions>3.4 avec check box "je ne suis pas en mesure de répondre à cette question"</functionalRestrictions>
    <q35Unknown>1</q35Unknown>
    <functionalRestrictions>3.5 avec checkbox "je ne suis pas en mesure de ..."</functionalRestrictions>
    <q36Unknown>0</q36Unknown>
    <doubtsForDrivingAbility>3.6 avec checkbox "je ne suis pas en mesure de ..."</doubtsForDrivingAbility>
</Seite6>
```

# page 7 (seite 7)
```xml
<Seite7>
    <header xfa:dataNode="dataGroup"/>
    <attachments></attachments>
    <providerS1Address>
        <condensedName></condensedName>
        <condensedAddress></condensedAddress>
        <ean>7601003002485</ean>
        <input></input>
    </providerS1Address>
    <formS1Struct>
        <modificationDate></modificationDate>
        <creationDate></creationDate>
        <serialNum></serialNum>
        <language>fr</language>
        <oid>medforms.40.10.5060</oid>
        <guid></guid>
        <version>101</version>
        <instructions>insuranceS1Address=(hidden) consumerS1Address=(hidden insuranceClone)
            producerS1Address=(hidden providerClone)
        </instructions>
    </formS1Struct>
    <informationForActivity></informationForActivity>
    <q41Unknown>0</q41Unknown>
    <suggestedWorkingHoursCurrent></suggestedWorkingHoursCurrent>
    <suggestedWorkingHoursOptimized></suggestedWorkingHoursOptimized>
    <prognosisForIntegration></prognosisForIntegration>
    <impedimentsForIntegration></impedimentsForIntegration>
    <q45Unknown>0</q45Unknown>
    <restrictionsInHousehold></restrictionsInHousehold>
</Seite7>
```

```xml
<Seite7>
    <header xfa:dataNode="dataGroup"/>
    <attachments>5 - p5 (annexes)</attachments>
    <providerS1Address>
        <condensedName>5 - p2</condensedName>
        <condensedAddress>5 - p3</condensedAddress>
        <ean>7601003002485</ean>
        <input/>
    </providerS1Address>
    <formS1Struct>
        <modificationDate>5 - p4</modificationDate>
        <creationDate/>
        <serialNum>?</serialNum>
        <language>fr</language>
        <oid>medforms.40.10.5060</oid>
        <guid/>
        <version>101</version>
        <instructions>insuranceS1Address=(hidden) consumerS1Address=(hidden insuranceClone)
            producerS1Address=(hidden providerClone)
        </instructions>
    </formS1Struct>
    <informationForActivity>5 - p1</informationForActivity>
    <q41Unknown>1</q41Unknown>
    <suggestedWorkingHoursCurrent>4.1 avec check box "je ne suis pas en mesure de ..."</suggestedWorkingHoursCurrent>
    <suggestedWorkingHoursOptimized>4.2</suggestedWorkingHoursOptimized>
    <prognosisForIntegration>4.3</prognosisForIntegration>
    <impedimentsForIntegration>4.4</impedimentsForIntegration>
    <q45Unknown>1</q45Unknown>
    <restrictionsInHousehold>4.5 avec checbox "je ne suis pas en mesure de ..."</restrictionsInHousehold>
</Seite7>
```


# structure générale : 
```xml
<xfa:datasets xmlns:xfa="http://www.xfa.org/schema/xfa-data/1.0/">
    <xfa:data>
        <mutter_dok>
            <Seite.../>
        </mutter_dok>
    </xfa:data>
</xfa:datasets>
```