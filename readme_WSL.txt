🛠️ Procédure pour mettre à jour l'APK
Dès que tu as modifié tes fichiers .py (ou tes images/assets) dans ton dossier Windows, suis ces étapes dans ton terminal WSL :

1. Synchroniser le code (Windows ➔ Linux)
On écrase les fichiers dans le dossier Linux avec tes nouvelles modifications :


cp -r /mnt/c/Users/thomt/Documents/WSL/FCVV_Viewer/* ~/FCVV_Viewer/

2. Activer l'environnement

conda activate buildozer_env

3. Exporter les correctifs (À faire une fois par session de terminal)
Pour que CMake et ton script de redirection fonctionnent :


export PATH=~/bin:$PATH

4. Compiler le nouvel APK
Tu n'as pas besoin de tout supprimer à chaque fois. Buildozer est capable de ne recompiler que ce qui a changé :

CMAKE_ARGS="-DCMAKE_POLICY_VERSION_MINIMUM=3.5" APP_ALLOW_MISSING_DEPS=true buildozer -v android debug

💡 Cas particuliers : Quand faire un "Clean" ?
Modification simple (ton code .py) : Ne fais pas de clean. Lance directement la commande de l'étape 4. Cela prendra moins de 2 minutes.

Changement dans buildozer.spec : Si tu ajoutes une bibliothèque dans requirements, il est souvent préférable de faire un petit nettoyage :


buildozer android clean

Note : Cela supprimera les bibliothèques compilées, mais pas le SDK Android (donc c'est assez rapide).

📁 Récupérer ton APK sur Windows
Une fois que tu vois # Android packaging done!, ton fichier est dans le dossier bin. Pour le copier sur ton Bureau Windows :


cp ~/FCVV_Viewer/bin/*.apk /mnt/c/Users/thomt/Desktop/

Rappel des commandes de secours (si erreur bizarre)
Si un jour la compilation bloque sans raison apparente :

Vérifie Cython : pip show cython (doit être en 0.29.36).

Vérifie le PATH : which cmake (doit renvoyer /home/thomthom/bin/cmake).

Gros nettoyage : Supprime le dossier .buildozer dans ton projet et relance tout.

***********************************************************************************************************************************
************************************************************************************************************************************

Pour une nouvelle application, la structure est déjà prête. Tu n'as plus besoin de réinstaller Python, Conda ou Buildozer. Il te suffit de suivre ce flux de travail "propre" :

1. Préparer le nouveau projet sur Windows
Crée ton nouveau dossier (ex: MonAutreApp) dans tes documents Windows et places-y ton main.py.

2. Transférer vers Linux (WSL)
Ouvre ton terminal WSL et copie ce nouveau dossier dans ton dossier "maison" :

cp -r /mnt/c/Users/thomt/Documents/Chemin/Vers/MonAutreApp ~/MonAutreApp
cd ~/MonAutreApp

3. Initialiser le projet
Génère le fichier de configuration spécifique à cette nouvelle application :

conda activate buildozer_env

5. Compiler
Utilise la commande avec les correctifs que nous avons mis en place :

export PATH=~/bin:$PATH
CMAKE_ARGS="-DCMAKE_POLICY_VERSION_MINIMUM=3.5" APP_ALLOW_MISSING_DEPS=true buildozer -v android debug
