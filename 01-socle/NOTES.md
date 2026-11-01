# Jalon 1 : socle Keycloak

## Objectif

Un Keycloak local avec deux utilisateurs, deux groupes et deux rôles.

## Environnement

- Système : Windows (version à noter)
- Java : (sortie de `java -version`)
- Keycloak : (version)
- Commande de démarrage : `bin\kc.bat start-dev`

## Ce que j'ai fait

1. Installation de Java.
2. Téléchargement et démarrage de Keycloak.
3. Création de l'administrateur.
4. Création du realm `labiam`.
5. Création des rôles `finance-user` et `it-user`.
6. Création des groupes `finance` et `it`, avec leur rôle.
7. Création des utilisateurs `alice` (finance) et `bob` (it).
8. Vérification de la connexion dans la console de compte.

## Preuves (captures, sans mot de passe ni secret)

- [ ] Le realm
- [ ] Les rôles
- [ ] Les groupes
- [ ] Un utilisateur avec ses groupes et ses rôles
- [ ] Connexion réussie d'alice et de bob

## Schéma

alice → groupe finance → rôle finance-user
bob → groupe it → rôle it-user

## Problèmes rencontrés et solutions

| Problème | Cause | Solution |
|---|---|---|
| | | |

## Ce que j'ai appris

-
-
-

## Suite

Jalon 2 : deux applications de test et matrice d'accès.
