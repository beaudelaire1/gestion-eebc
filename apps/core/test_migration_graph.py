"""Garde-fou sur le graphe de migrations.

Une migration qui crée un objet déjà présent dans l'état du projet est acceptée
sans bruit par SQLite mais rejetée par PostgreSQL. Le déploiement Coolify a
échoué exactement ainsi :

    column "is_pinned" of relation "communication_announcement" already exists

Ce test rejoue tout le graphe opération par opération, sans base de données, de
sorte que ce type de dérive soit détecté avant un déploiement sur PostgreSQL.
"""

from django.db import migrations
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState


def _forwards_plan(graph):
    plan = []
    seen = set()
    for target in sorted(graph.leaf_nodes()):
        for node in graph.forwards_plan(target):
            if node not in seen:
                seen.add(node)
                plan.append(node)
    return plan


def _duplicate_ddl_operations():
    loader = MigrationLoader(None, ignore_no_migrations=True)
    graph = loader.graph
    state = ProjectState()
    duplicates = []

    for node in _forwards_plan(graph):
        migration = graph.nodes[node]
        app_label = migration.app_label
        label = f'{node[0]}.{node[1]}'

        for operation in migration.operations:
            if isinstance(operation, migrations.AddField):
                model_state = state.models.get((app_label, operation.model_name_lower))
                if model_state and operation.name in model_state.fields:
                    duplicates.append(
                        f'{label}: AddField {operation.model_name}.{operation.name}'
                    )
            elif isinstance(operation, migrations.CreateModel):
                if (app_label, operation.name_lower) in state.models:
                    duplicates.append(f'{label}: CreateModel {operation.name}')
            elif isinstance(operation, migrations.AddIndex):
                model_state = state.models.get((app_label, operation.model_name_lower))
                if model_state and any(
                    index.name == operation.index.name
                    for index in model_state.options.get('indexes', [])
                ):
                    duplicates.append(f'{label}: AddIndex {operation.index.name}')

            # L'état doit avancer opération par opération : un remove suivi d'un
            # add dans la même migration n'est pas un doublon.
            operation.state_forwards(app_label, state)

    return duplicates


def test_no_migration_recreates_an_existing_database_object():
    duplicates = _duplicate_ddl_operations()

    assert not duplicates, (
        'Ces migrations émettent du DDL pour un objet déjà présent dans '
        "l'état du projet et échoueront sur PostgreSQL :\n  - "
        + '\n  - '.join(duplicates)
    )
