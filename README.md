# identity-access-lab

Authentification, autorisation et détection avec Keycloak, Kubernetes et Wazuh.

Labo personnel pour comprendre et démontrer la gestion des identités et des accès (IAM) : qui peut se connecter, qui peut accéder à quoi, et comment le vérifier dans les journaux.

## Question centrale

Un utilisateur peut s'authentifier sans être autorisé : se connecter ne donne pas accès aux ressources. Ce labo montre pourquoi et comment le diagnostiquer.

## Scénario

Deux utilisateurs, deux groupes, deux applications.

| | Application Compta (rôle `finance-user`) | Application Serveurs (rôle `it-user`) |
|---|---|---|
| alice (groupe `finance`) | Oui | Non |
| bob (groupe `it`) | Non | Oui |

Chaîne d'accès : utilisateur, groupe, rôle, permission, ressource. Par défaut, tout est refusé (moindre privilège).

## Jalons

| Jalon | Contenu | État |
|---|---|---|
| 1. Socle | Keycloak local, realm, utilisateurs, groupes, rôles | À faire |
| 2. Autorisation | Deux applications de test, matrice des 4 cas, erreurs 403 | À faire |
| 3. Sécurisation | MFA, politique de mot de passe, durée des sessions | À faire |
| 4. Journaux et détection | Événements envoyés à Wazuh ou Splunk, 2 ou 3 alertes | À faire |
| 5. Kubernetes (option) | Connexion OIDC avec Keycloak, RBAC au moindre privilège | À faire |

## Prérequis

- Windows, 16 Go de RAM recommandés
- OpenJDK (version exigée par la version de Keycloak utilisée)
- Keycloak, installé depuis l'archive zip (non versionné dans ce dépôt)

## Reproduire le labo

À compléter à la fin de chaque jalon.

## Sécurité

- Labo local uniquement : Keycloak en mode `start-dev`, jamais exposé sur Internet.
- Aucun vrai compte, aucun vrai mot de passe, aucun secret dans ce dépôt.

## Limites et suite

À compléter.
