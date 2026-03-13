COBOL Call Flow Analyzer
Objectif

Construire un analyseur COBOL capable de :

scanner un dossier racine et ses sous-dossiers

détecter tous les programmes COBOL disponibles

construire un index des PROGRAM-ID

parser les programmes IBM Enterprise COBOL

résoudre les appels inter-programmes

suivre récursivement les sous-programmes présents dans le périmètre

produire un graphe de flux

exporter ce graphe en flowchart SVG

Le système doit d’abord répondre à cette question :

à partir d’un programme d’entrée, quels programmes, paragraphes, conditions et appels peuvent être exécutés, et sous quelle forme les représenter visuellement ?

Périmètre fonctionnel visé
Entrée

un dossier racine A

un programme d’entrée (PROGRAM-ID ou fichier)

éventuellement des variables initiales

éventuellement des copybooks accessibles dans un ou plusieurs dossiers

Sortie

Le système doit produire :

un index des programmes

un graphe d’appels

un graphe de contrôle simplifié

un flowchart SVG

éventuellement du JSON intermédiaire pour debug et réutilisation

Vision d’ensemble

Le projet doit être découpé en plusieurs couches.

1. Découverte des sources

Responsabilité :

parcourir récursivement le dossier racine

identifier les fichiers COBOL

extraire les PROGRAM-ID

construire un index global

2. Prétraitement COBOL

Responsabilité :

gérer le fixed format IBM

ignorer les séquences/colonnes

résoudre les COPY

isoler la PROCEDURE DIVISION

nettoyer les lignes

3. Parsing

Responsabilité :

construire un AST simplifié par programme

détecter :

paragraphes

IF / ELSE / END-IF

EVALUATE / WHEN / END-EVALUATE

PERFORM

PERFORM THRU

CALL

CALL 'ZCALLPGM' USING ...

MOVE

SET

COMPUTE

READ

EXEC SQL

4. Résolution inter-programmes

Responsabilité :

déterminer si un CALL cible un programme connu

distinguer :

appels littéraux

appels dynamiques

trampoline type ZCALLPGM

suivre récursivement les dépendances présentes dans le dossier racine

5. Analyse de flot

Responsabilité :

exécuter symboliquement les conditions

propager les variables connues

fork sur les conditions inconnues

produire des chemins d’exécution plausibles

6. Construction du flowchart

Responsabilité :

transformer les résultats d’analyse en nœuds et arêtes

produire une représentation hiérarchique lisible

exporter en SVG

Résultat attendu côté utilisateur

L’utilisateur doit pouvoir lancer quelque chose comme :

python main.py scan ./src_cobol --entry PGMB002 --svg out/flow.svg

ou :

python main.py analyze ./src_cobol --entry PGMB002 --vars WS-FLAG=true --svg out/flow.svg

Et obtenir :

un fichier flow.svg

un JSON de debug

éventuellement un résumé console

Architecture recommandée
Arborescence proposée
cobol-flow-analyzer/
├── main.py
├── README.md
├── requirements.txt
├── src/
│   ├── discovery/
│   │   ├── file_scanner.py
│   │   ├── program_indexer.py
│   │   └── models.py
│   ├── preprocess/
│   │   ├── ibm_fixed_format.py
│   │   ├── copybook_resolver.py
│   │   └── procedure_extractor.py
│   ├── parser/
│   │   ├── ast_nodes.py
│   │   ├── cobol_parser.py
│   │   ├── paragraph_detector.py
│   │   └── statement_parser.py
│   ├── analysis/
│   │   ├── symbolic_executor.py
│   │   ├── call_resolver.py
│   │   ├── call_graph_builder.py
│   │   └── state_models.py
│   ├── render/
│   │   ├── graph_model.py
│   │   ├── flowchart_builder.py
│   │   ├── svg_renderer.py
│   │   └── mermaid_exporter.py
│   └── utils/
│       ├── logging_utils.py
│       └── text_utils.py
├── tests/
│   ├── test_discovery.py
│   ├── test_parser.py
│   ├── test_symbolic_executor.py
│   ├── test_call_graph.py
│   └── test_svg_renderer.py
└── examples/
    ├── PGMA001.cbl
    ├── PGMB002.cbl
    └── CPYBATCH.cpy
Modèle de données recommandé
Programme source
@dataclass
class ProgramSource:
    program_id: str
    path: str
    raw_text: str | None = None
Index global
ProgramIndex = dict[str, ProgramSource]
AST simplifié

Chaque programme doit au minimum contenir :

son PROGRAM-ID

ses paragraphes

l’ordre des paragraphes

les statements structurés

Référence d’appel
@dataclass
class CallRef:
    caller_program: str
    raw_target: str
    resolved_target: str | None
    using_args: list[str]
    is_dynamic: bool
    is_external: bool
    is_found_in_index: bool
Analyse d’un programme
@dataclass
class ProgramAnalysis:
    program_id: str
    path: str
    paragraphs: list[str]
    calls: list[CallRef]
    warnings: list[str]
    errors: list[str]
Graphe global
@dataclass
class CallGraph:
    nodes: dict[str, ProgramAnalysis]
    edges: list[tuple[str, str]]
    missing_edges: list[tuple[str, str]]
Nœud de flowchart
@dataclass
class FlowNode:
    id: str
    label: str
    kind: str  # start, process, decision, call, end

@dataclass
class FlowEdge:
    source: str
    target: str
    label: str | None = None
Étapes d’implémentation
Étape 1 — Scanner les programmes
Objectif

Construire un index fiable des programmes disponibles dans le dossier racine.

À faire

parcourir tous les fichiers .cbl, .cob, éventuellement .txt

lire le PROGRAM-ID

associer PROGRAM-ID -> chemin

signaler les doublons

Sortie

Un dictionnaire global des programmes disponibles.

Critère de validation

À la fin, tu peux afficher :

Programs found:
- PGMA001 -> ...
- PGMB002 -> ...
- ZCALLPGM -> ...
Étape 2 — Prétraiter le COBOL
Objectif

Normaliser les fichiers COBOL avant parsing.

À faire

gérer le fixed format IBM

ignorer les commentaires

gérer les COPY

consommer correctement le header PROCEDURE DIVISION USING ...

ne conserver que la PROCEDURE DIVISION

Critère de validation

Afficher les lignes réellement données au parseur.

Étape 3 — Construire l’AST simplifié
Objectif

Construire une représentation exécutable du programme.

À faire

Détecter les paragraphes et parser au moins :

MOVE

SET

COMPUTE

IF / ELSE / END-IF

EVALUATE / WHEN / END-EVALUATE

PERFORM

PERFORM THRU

CALL

READ

EXEC SQL

Critère de validation

Afficher :

Paragraphs found: [...]

et vérifier que tous les paragraphes attendus sont là.

Étape 4 — Construire le graphe d’appels
Objectif

Savoir qui appelle qui dans le périmètre du dossier.

À faire

Pour chaque programme :

détecter les CALL

résoudre les cibles littérales

résoudre les cibles dynamiques si possible

identifier les appels internes vs externes

Cas spécifiques à gérer

CALL 'PGMA001'

CALL WS-PGM-NAME

CALL 'ZCALLPGM' USING WS-PGM-NAME ...

Critère de validation

Obtenir un graphe du type :

PGMB002 -> ZCALLPGM
ZCALLPGM -> PGMA001
Étape 5 — Ajouter l’exécution symbolique
Objectif

Parcourir les branches possibles.

À faire

injecter un état initial

propager les affectations

évaluer les conditions

forker en cas d’incertitude

tracer les paragraphes visités

tracer les appels effectués

Critère de validation

Obtenir des chemins tels que :

PATH #1
- PERFORM 1000-INIT
- IF CPYB-AMOUNT > 10000 => THEN
- CALL PGMA001
Étape 6 — Définir le modèle visuel
Objectif

Créer une représentation commune pour tous les rendus.

Types de nœuds

start

end

paragraph

process

decision

call

external_call

unknown_branch

Types d’arêtes

séquentielle

branche THEN

branche ELSE

appel vers sous-programme

retour éventuel

Règle importante

Le modèle visuel doit être indépendant du moteur SVG.
Il faut d’abord construire un graphe abstrait, puis le rendre.

Étape 7 — Exporter en SVG
Objectif

Générer un vrai flowchart lisible.

Deux approches possibles
Option A — Graphviz

Avantages :

rapide à implémenter

layout automatique

export SVG natif

Inconvénients :

moins de contrôle fin

dépendance externe

Option B — SVG natif maison

Avantages :

contrôle total du rendu

facilement intégrable plus tard dans une UI

Inconvénients :

layout plus dur à faire

Recommandation

Commencer par Graphviz pour valider le concept, puis migrer plus tard si besoin.

Représentation visuelle recommandée
Niveau 1 — Call graph global

Exemple :

PGMB002
 └── ZCALLPGM
      └── PGMA001

Usage :

vue architecture

dépendances entre programmes

Niveau 2 — Flowchart d’un programme

Exemple :

[0000-MAIN]
   ↓
[PERFORM 1000-INIT]
   ↓
[PERFORM 2000-VALIDATE]
   ↓
<CPYB-VALIDATION-KO ?>
  ├─ Oui → [9000-FINALIZE] → [GOBACK]
  └─ Non → [3000-BUSINESS-DISPATCH]

Usage :

lecture logique

compréhension métier

Niveau 3 — Flowchart inter-programmes

Exemple :

PGMB002:3500-OPTIONAL-CALL
   ↓
CALL ZCALLPGM
   ↓
resolve WS-PGM-NAME = PGMA001
   ↓
PGMA001:0000-MAIN

Usage :

parcours bout en bout

SVG attendu

Le SVG doit idéalement permettre :

des boîtes rectangulaires pour les actions

des losanges pour les décisions

des flèches annotées

un style distinct pour les appels externes

une hiérarchie visuelle claire

Convention visuelle suggérée

rectangle : traitement / paragraphe

losange : condition

rectangle à bord épais : call programme

rectangle grisé : programme introuvable

pointillé : branche incertaine / unknown

couleur douce : programme local

couleur différente : call externe

Algorithme de construction du graphe
Pour le call graph

1 nœud par programme

1 arête par appel résolu

1 arête spéciale pour appel externe

Pour le flowchart

1 nœud d’entrée par paragraphe principal

1 nœud par statement significatif

arêtes selon ordre d’exécution

bifurcation sur IF et EVALUATE

saut sur PERFORM THRU

entrée spéciale lors d’un CALL

Gestion des appels
Appel littéral
CALL 'PGMA001'

Résolution directe dans l’index.

Appel dynamique
CALL WS-PGM-NAME

si WS-PGM-NAME est connu dans l’état : résolution

sinon : branche inconnue

Trampoline ZCALLPGM
CALL 'ZCALLPGM' USING WS-PGM-NAME ...

Deux niveaux doivent pouvoir être représentés :

le trampoline technique ZCALLPGM

la cible métier réelle WS-PGM-NAME -> PGMA001

Limites à accepter dans la première version

La V1 n’a pas besoin de tout faire.

Peut être hors périmètre V1

COPY ... REPLACING

sections complexes

plusieurs programmes dans un même fichier

GO TO DEPENDING ON

SQL finement interprété

88-level avancés

layout SVG ultra sophistiqué

Objectif réaliste V1

dossier scanné

programmes indexés

graphe d’appels fiable

flowchart SVG lisible

appels internes suivis récursivement

Roadmap suggérée
V1 — squelette fonctionnel

scan dossier

index PROGRAM-ID

parse paragraphes

détecter CALL

exporter call graph simple en SVG

V2 — contrôle de flux

IF

EVALUATE

PERFORM

PERFORM THRU

flowchart intra-programme

V3 — inter-programmes

récursion sur programmes présents dans le dossier

résolution trampoline ZCALLPGM

flowchart inter-programmes

V4 — analyse symbolique

propagation MOVE / SET / COMPUTE

fork sur conditions inconnues

branches pointillées dans le SVG

V5 — industrialisation

JSON export

cache AST

CLI complète

logs

tests

gestion des gros volumes

Fichiers de sortie recommandés

Pour une analyse donnée :

output/
├── program_index.json
├── call_graph.json
├── call_graph.svg
├── flow_PGMB002.svg
├── flow_PGMA001.svg
└── trace_paths.json
Stratégie de tests
Tests unitaires

extraction PROGRAM-ID

parsing PROCEDURE DIVISION

IF

EVALUATE

PERFORM THRU

CALL

Tests d’intégration

PGMB002 -> ZCALLPGM -> PGMA001

flowchart généré

SVG non vide

programmes manquants correctement signalés

Jeux de test

Tu as déjà une bonne base avec :

PGMA001

PGMB002

CPYBATCH

Choix techniques conseillés
Langage

Python

Bibliothèques possibles

graphviz pour la V1 du SVG

dataclasses

pathlib

re

json

À éviter au début

parser COBOL complet type grammaire totale

moteur graphique custom trop tôt

optimisation prématurée

Bonnes pratiques d’implémentation

séparer discovery, parse, analysis, render

garder un modèle intermédiaire JSON sérialisable

ne jamais mélanger parsing et rendu SVG

loguer systématiquement :

paragraphes trouvés

appels trouvés

cibles résolues

cibles manquantes

prévoir un mode debug lisible

Exemple de rendu attendu
Call graph simple
PGMB002
 ├── ZCALLPGM
 └── external: LOGPGM

ZCALLPGM
 └── PGMA001
Flowchart logique
[0000-MAIN]
   ↓
[1000-INIT]
   ↓
[2000-OPEN-FILE]
   ↓
<WS-INFILE-STATUS != '00'>
   ├── Yes → [DISPLAY ERROR] → [GOBACK]
   └── No  → [3000-READ-LOOP]
Définition de done

Le système sera considéré comme “done” pour une première vraie version quand il saura :

scanner un dossier COBOL

identifier les programmes disponibles

analyser un programme racine

suivre récursivement les sous-programmes présents dans le dossier

produire un flowchart SVG lisible

distinguer appels résolus / non résolus

fournir un JSON de debug exploitable

Résumé

Le projet doit être pensé comme :

indexer

parser

résoudre

analyser

rendre

L’erreur classique serait de vouloir générer le SVG directement depuis le parseur.
Il faut au contraire :

un modèle COBOL

un modèle d’analyse

un modèle de graphe visuel

puis seulement le rendu SVG