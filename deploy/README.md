# Mise en service du déploiement continu (une seule fois)

À exécuter dans l'ordre. Les commandes marquées **[sudo]** demandent le mot de passe du compte `<compte_admin>` sur le VPS (le compte `<compte_admin>` doit avoir un mot de passe pour pouvoir utiliser `sudo`, à définir avec `passwd` si besoin).
Rien de ce qui existe déjà sur le serveur (vhosts, conteneurs, ports) n'est modifié. Le VPS héberge d'autres applications en production : toutes les étapes ci-dessous se limitent à FasoSearch.

## 1. DNS

Créer un enregistrement **A** `fasosearch.golden-technologies.com` vers `<IP_DU_VPS>`, puis vérifier :
`getent hosts fasosearch.golden-technologies.com`

## 2. Dépôt GitHub

Créer le dépôt **public** `abdazz/fasosearch` (sans README ni licence), puis depuis `sri/` :
```bash
git remote add origin git@github.com:abdazz/fasosearch.git
git push -u origin main
```
Le premier workflow échouera à l'étape « deploy » tant que les étapes 3 à 7 ne sont pas faites : c'est normal. Ce premier push crée automatiquement l'environnement `production` (configuré à l'étape 7) et le paquet d'image `ghcr.io/abdazz/fasosearch`.

Une fois le paquet publié (fin du job « build ») : sur GitHub, profil → Packages → `fasosearch` → Package settings → Change visibility → **Public**. L'image devient téléchargeable sans authentification (retour arrière manuel sur le VPS, tests locaux).

## 3. Clé SSH dédiée (sur votre PC)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/fasosearch_deploy_key -C "deploiement-fasosearch" -N ""
ssh-keyscan -t ed25519 <IP_DU_VPS> > fasosearch_known_hosts
```

Vérifier l'empreinte avant de faire confiance à ce résultat : sur le VPS, `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub` doit afficher la même empreinte (SHA256) que celle de la clé récupérée par `ssh-keyscan`, obtenue en exécutant `ssh-keygen -lf fasosearch_known_hosts` en local. Ne pas continuer si les deux empreintes ne correspondent pas.

## 4. Utilisateur `deploy` (sur le VPS, connecté en `<compte_admin>`)

Ce compte est dédié à FasoSearch : ne pas le réutiliser pour une autre application du VPS (le workflow exécute `docker logout ghcr.io` avec ce compte à la fin de chaque déploiement, ce qui déconnecterait aussi les autres usages).

Depuis le PC, copier la clé publique sur le VPS :
```bash
scp ~/.ssh/fasosearch_deploy_key.pub <compte_admin>@<IP_DU_VPS>:/tmp/fasosearch_deploy_key.pub
```
Puis, sur le VPS, connecté en `<compte_admin>` :
```bash
sudo adduser --disabled-password --gecos "" deploy        # [sudo]
sudo usermod -aG docker deploy                             # [sudo]
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh                    # [sudo]
sudo tee -a /home/deploy/.ssh/authorized_keys < /tmp/fasosearch_deploy_key.pub   # [sudo]
sudo chown deploy:deploy /home/deploy/.ssh/authorized_keys && sudo chmod 600 /home/deploy/.ssh/authorized_keys   # [sudo]
rm /tmp/fasosearch_deploy_key.pub
sudo install -d -o deploy -g deploy /opt/fasosearch        # [sudo]
sudo -u deploy touch /opt/fasosearch/.env                  # [sudo]
```
Le fichier `.env` reste vide : le premier déploiement y inscrit le SHA déployé (aucune version précédente n'existe encore, donc aucun retour arrière possible à ce stade).
Vérifier depuis le PC : `ssh -i ~/.ssh/fasosearch_deploy_key deploy@<IP_DU_VPS> docker ps` doit afficher la liste des conteneurs.

## 5. Apache

Depuis le PC, dans `sri/`, copier la configuration sur le VPS :
```bash
scp deploy/apache/fasosearch.conf <compte_admin>@<IP_DU_VPS>:/tmp/
```
Puis, sur le VPS, connecté en `<compte_admin>` :
```bash
sudo a2enmod proxy proxy_http                                                   # [sudo]
sudo cp /tmp/fasosearch.conf /etc/apache2/sites-available/fasosearch.golden-technologies.com.conf  # [sudo]
sudo a2ensite fasosearch.golden-technologies.com.conf                           # [sudo]
sudo apache2ctl configtest && sudo systemctl reload apache2                      # [sudo]
```
`proxy` et `proxy_http` sont déjà activés sur ce VPS pour les autres applications : la commande `a2enmod` ne modifie rien dans ce cas (sans danger de la relancer).

## 6. HTTPS (sur le VPS, après propagation DNS)

```bash
sudo certbot --apache -d fasosearch.golden-technologies.com --redirect          # [sudo]
```

## 7. Environnement `production` et secrets GitHub

Dépôt → Settings → Environments → `production` (déjà créé par le premier push de l'étape 2 : le modifier, ne pas en créer un nouveau).

1. Sous « Deployment branches and tags », choisir **Selected branches and tags** et n'autoriser que `main`.
2. Sous « Environment secrets », ajouter les quatre secrets ci-dessous (**Add environment secret**). Ne pas les créer comme secrets du dépôt (Settings → Secrets and variables → Actions → Repository secrets) : un secret de dépôt est lisible par un workflow lancé depuis n'importe quelle branche.

| Secret | Valeur |
|---|---|
| `VPS_HOST` | `<IP_DU_VPS>` |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | contenu de `~/.ssh/fasosearch_deploy_key` (clé **privée**) |
| `VPS_KNOWN_HOSTS` | contenu de `fasosearch_known_hosts` (voir étape 3, empreinte vérifiée) |

La restriction à `main` ne protège les secrets que parce qu'ils sont des secrets de l'environnement : seul un job qui déclare `environment: production` et s'exécute sur `main` peut les lire. Une autre branche, même avec un workflow modifié, ne reçoit ni la clé SSH ni l'adresse du VPS. Si un ancien secret `VPS_*` existe au niveau du dépôt, le supprimer.

## 8. Premier déploiement

Actions → CI/CD → Run workflow (branche `main`, étiquette vide). Le premier build (construction de l'index) prend environ 25 à 35 minutes ; les suivants ne prennent que quelques minutes grâce au cache. Vérifier ensuite https://fasosearch.golden-technologies.com

## Opérations courantes

- **Mettre à jour le site :** commit, puis push sur `main`.
- **Revenir à une version :** Actions → CI/CD → Run workflow avec `image_tag` = SHA complet (40 caractères hexadécimaux, `git rev-parse <commit>`) d'un commit déjà déployé ; un SHA court est refusé par le workflow, car les images ne sont publiées que sous le SHA complet. Le workflow accepte aussi `latest`, mais c'est déconseillé pour un retour arrière : `latest` est publié avant la vérification en production et peut donc désigner la version défectueuse. Alternative directe sur le VPS, connecté en `<compte_admin>` (le fichier `.env` appartient à `deploy`) : `sudo -u deploy bash /opt/fasosearch/remote-deploy.sh rollback` **[sudo]**.
- **Journaux :** `ssh -i ~/.ssh/fasosearch_deploy_key deploy@<IP_DU_VPS> docker logs --tail 100 fasosearch`.
