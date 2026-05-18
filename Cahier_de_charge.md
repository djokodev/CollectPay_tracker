# Nom du projet: CollectPay Tracker

Type de projet: Plateforme de suivi des paiements entrants Mobile Money.

## Contexte
Au Cameroun, beaucoup de structures encaissent de l’argent via Mobile Money, mais le suivi des paiements reste souvent manuel. Les confirmations passent par WhatsApp, appels, captures d’écran ou fichiers Excel. Cela crée des erreurs, des oublis, des doublons et un manque de visibilité rapide.

## Problème
Les organisations ont besoin de savoir clairement qui a payé, combien, quand, pour quel service et avec quel statut. Le manque de traçabilité rend le suivi administratif difficile.


## Utilisateurs cibles

Le projet peut viser :
écoles ;
associations ;
tontines ;
petits commerces ;
centres de formation ;
plateformes locales ;
organisateurs d’événements ;
micro-entreprises ;
responsables administratifs.


## Objectif métier

Permettre à une organisation de savoir rapidement :
qui doit payer ;
qui a déjà payé ;
combien a été payé ;
quand le paiement a été reçu ;
pour quel service ;
quel est le statut du paiement ;
quel montant reste à recevoir ;



## Fonctionnalités : 

1. Authentification

Tu dois permettre à un utilisateur de se connecter.

Fonctionnalités :

inscription d’un administrateur ;
connexion ;
déconnexion ;
gestion du profil ;
permissions selon le rôle.

Notions à maîtriser :
JWT ;
permissions Django REST Framework ;
rôles utilisateurs ;
sécurité des endpoints.

2. Gestion des organisations

Comme plusieurs structures peuvent utiliser le système, il faut prévoir une notion d’organisation.

Exemple :
École La Réussite ;
Tontine Solidarité ;
Centre de formation X ;
Boutique Y.

Une organisation possède ses propres clients, services et paiements.

Fonctionnalités :
créer une organisation ;
modifier les informations ;
lier les utilisateurs à une organisation ;
filtrer les données par organisation.

Notions à maîtriser :
architecture multi-tenant simple ;
isolation des données ;
relations entre modèles Django.

3. Gestion des clients ou payeurs

Un payeur est une personne qui doit effectuer un paiement.

Exemple :
étudiant ;
parent ;
membre d’une tontine ;
participant à un événement. 
etc...

Champs possibles :
Nom
Téléphone
Email optionnel
Référence client
Organisation
Date de création
etc...

Fonctionnalités :
créer un client ;
modifier un client ;
rechercher un client ;
voir l’historique de ses paiements ;
désactiver un client.
etc..

Notions à maîtriser :
CRUD ;
pagination ;
recherche ;
filtres API.

4. Gestion des services ou motifs de paiement

Un paiement doit toujours être lié à une raison claire.

Exemples :
frais d’inscription ;
frais de scolarité ;
cotisation mensuelle ;
achat produit ;
participation événement ;
abonnement ;
avance ;
solde restant.
etc..

Champs possibles :
Nom du service
Description
Montant attendu
Devise
Organisation
Statut actif/inactif
etc..

Fonctionnalités :
créer un service ;
définir un montant ;
lier un service à un paiement ;
désactiver un service.
etc..

5. Création d’une demande de paiement

C’est le cœur du projet.

Une demande de paiement représente quelque chose qu’un client doit payer.

Exemple : Djoko doit payer 25 000 FCFA pour les frais d’inscription.

Champs possibles :
Client
Service
Montant attendu
Montant payé
Statut
Date limite optionnelle
Référence unique
Organisation
Créé par
Date de création
etc..

Statuts possibles :
PENDING = En attente
PARTIAL = Paiement partiel
PAID = Payé
FAILED = Échoué
CANCELLED = Annulé
REFUNDED = Remboursé

Fonctionnalités :
créer une demande ;
consulter les paiements en attente ;
mettre à jour le statut ;
gérer le paiement partiel ;
consulter les paiements en retard ;
générer une référence unique.
etc..

6. Enregistrement d’un paiement reçu

Ici, on enregistre une transaction.

Au début, cette transaction peut être saisie manuellement par un agent ou un admin.

Exemple : Un client envoie 25 000 FCFA par Orange Money. L’agent vérifie et enregistre :

Montant reçu : 25 000
Opérateur : Orange Money
Numéro payeur : 699000000
Référence transaction : OM123456
Date de paiement : 05/05/2026
Statut : confirmé

Champs possibles :
PaymentRequest
Montant reçu
Méthode de paiement
Opérateur
Numéro de téléphone
Référence transaction
Statut transaction
Date de paiement
Confirmé par
Notes

Méthodes de paiement possibles :
ORANGE_MONEY
MTN_MOMO
CASH
BANK_TRANSFER
OTHER

Fonctionnalités :
enregistrer une transaction ;
éviter les doublons sur la référence transaction ;
vérifier si le montant payé correspond au montant attendu ;
mettre à jour automatiquement le statut de la demande ;
garder l’historique.

Notion importante ici : idempotence.

C’est une notion très importante dans les systèmes de paiement. Elle permet d’éviter qu’une même transaction soit enregistrée deux fois.

7. Reçus numériques

Après confirmation d’un paiement, le système doit pouvoir générer un reçu.

Le reçu peut contenir :
Nom de l’organisation
Nom du client
Montant payé
Service payé
Date
Référence paiement
Méthode de paiement
Statut
Signature ou code de vérification
etc..

Fonctionnalités :
générer un reçu ;
consulter un reçu ;
télécharger un reçu ;
vérifier un reçu avec une référence publique.

Notions à apprendre :
génération de PDF avec Python ;
URLs publiques sécurisées ;
UUID ;
hash de vérification.

8. Tableau de bord backend

Cote frontend, permettre de récupérer des statistiques depuis l'APU

Exemples :
Total encaissé aujourd’hui
Total encaissé ce mois
Nombre de paiements en attente
Nombre de paiements confirmés
Nombre de paiements partiels
Montant total attendu
Montant total reçu
Écart restant

Notions à maîtriser :
agrégations Django ORM ;
annotate ;
Sum ;
Count ;
filtres par date ;
performance des requêtes.

9. Exports

Les responsables aiment souvent travailler avec Excel. Donc l’export est important.

Fonctionnalités :
exporter les paiements en CSV ;
filtrer avant export ;
exporter par période ;
exporter par statut ;
exporter par client ou service.

Formats possibles :
CSV, Excel et PDF 

Notions à apprendre :
génération CSV, Excel et PDF en Django ;


## Règles métier importantes :

- Règle 1 : une transaction confirmée ne doit pas être enregistrée deux fois. Si une référence transaction existe déjà, le système doit refuser le doublon.
- Règle 2 : si le montant payé est inférieur au montant attendu, le statut devient PARTIAL
Exemple :
Montant attendu : 50 000 FCFA
Montant payé : 30 000 FCFA
Statut : PARTIAL
Reste : 20 000 FCFA
- Règle 3 : si le montant payé est égal ou supérieur au montant attendu, le statut devient PAID
Exemple :
Montant attendu : 50 000 FCFA
Montant payé : 50 000 FCFA
Statut : PAID
- Règle 4 : un paiement annulé ne doit plus accepter de transaction
Si une demande de paiement est annulée, on ne doit plus pouvoir enregistrer un paiement dessus.
- Règle 5 : toutes les actions sensibles doivent être historisées
Exemples :
Qui a confirmé le paiement ?
Quand ?
Quel montant ?
Quelle référence ?
Quel statut avant ?
Quel statut après ?


Périmètre : On vas developper le projet en deux phases, la premier constiste a developper toute la plateforme sans integration
mobile money. Et puis la deuxieme phase consiste a integrer MTN et ORANGE Money dans la plateforme afin que les clients puisse faire directemnent les paiments depuis la plateforme, dans la premier phase on vas ce contenter d'enregister manuellement.


Stack Technique: Backend(Django) ; Frontend(HTMX + Alpine.js + TailwindCSS)