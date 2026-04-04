from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, Any


class CopyLookupError(Exception):
    """Exception de base pour CopyLookup."""


class CopyNotFoundError(CopyLookupError):
    """Levée lorsqu'une copy n'existe pas dans l'index."""


class CopyLookupNotInitializedError(CopyLookupError):
    """Levée lorsqu'aucune configuration exploitable n'est disponible."""


class _CopyLookup:
    """
    Singleton chargé :
    - d'indexer les fichiers COPY (.cpy, .cpm, .cpx)
    - de sauvegarder / recharger cet index
    - de résoudre un nom de copy vers son chemin réel

    Format du JSON de sauvegarde :
    {
      "source_root_folder": "H:/sources/cobol",
      "index": {
        "COPYA": "H:/sources/cobol/cpy/COPYA.cpy",
        "COPYB": "H:/sources/cobol/common/COPYB.cpm"
      }
    }
    """

    _instance: Optional["_CopyLookup"] = None
    _lock: Lock = Lock()

    VALID_EXTENSIONS = {".cpy", ".cpm", ".cpx"}

    def __new__(
        cls,
        root_folder: Optional[str] = None,
        save_file: str = "copy_index.json"
    ) -> "_CopyLookup":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        root_folder: Optional[str] = None,
        save_file: str = "copy_index.json"
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self.save_file = Path(save_file).resolve()
        self.source_root_folder: Optional[Path] = Path(root_folder).resolve() if root_folder else None
        self.index: Dict[str, str] = {}

        self._auto_load_from_disk()

        self._initialized = True

    @classmethod
    def get_instance(cls) -> "_CopyLookup":
        if cls._instance is None:
            raise CopyLookupNotInitializedError(
                "CopyLookup n'a pas encore été initialisé."
            )
        return cls._instance

    def build_index(self, folder_path: str) -> Dict[str, str]:
        """
        Méthode 1 : création de l'index.

        - prend le chemin d'un dossier en entrée
        - examine dans tous les dossiers et sous-dossiers les fichiers
          .cpy / .cpm / .cpx
        - construit un dictionnaire :
              nom du fichier sans extension => chemin réel complet
        - met à jour l'index en mémoire
        - met à jour le dossier source en mémoire
        - retourne le dictionnaire
        """
        #print(f"Building copy index from folder: {folder_path}")
        root = Path(folder_path).resolve()

        if not root.exists() or not root.is_dir():
            raise ValueError(f"Le dossier fourni n'existe pas ou n'est pas un dossier : {root}")

        new_index: Dict[str, str] = {}

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            if file_path.suffix.lower() not in self.VALID_EXTENSIONS:
                continue

            copy_name = file_path.stem.upper()
            real_path = str(file_path.resolve())

            if copy_name in new_index:
                raise CopyLookupError(
                    f"Collision détectée pour la copy '{copy_name}'. "
                    f"Plusieurs fichiers portent ce nom :\n"
                    f"- {new_index[copy_name]}\n"
                    f"- {real_path}"
                )

            new_index[copy_name] = real_path
            #print(f"Indexed copy: {copy_name} => {real_path}")

        self.source_root_folder = root
        self.index = new_index
        return new_index

    def update_saved_index(self) -> Dict[str, Any]:
        """
        Méthode 2 : sauvegarde et mise à jour de l'index.

        - lit la sauvegarde
        - reconstruit l'index actuel à partir du dossier source connu
        - détecte les différences
        - met à jour le fichier de sauvegarde
        - retourne un résumé des différences
        """
        saved_payload = self._load_saved_payload()
        saved_index = saved_payload.get("index", {})
        saved_root = saved_payload.get("source_root_folder")

        if self.source_root_folder is None:
            if saved_root:
                self.source_root_folder = Path(saved_root).resolve()
            else:
                raise CopyLookupNotInitializedError(
                    "Aucun dossier source connu. "
                    "Initialise CopyLookup avec root_folder ou fournis un JSON valide."
                )

        current_index = self.build_index(str(self.source_root_folder))

        added = {
            k: v for k, v in current_index.items()
            if k not in saved_index
        }

        removed = {
            k: v for k, v in saved_index.items()
            if k not in current_index
        }

        changed = {
            k: {
                "old": saved_index[k],
                "new": current_index[k],
            }
            for k in current_index
            if k in saved_index and saved_index[k] != current_index[k]
        }

        source_root_changed = (saved_root is not None and saved_root != str(self.source_root_folder))

        self._save_payload(
            source_root_folder=str(self.source_root_folder),
            index=current_index
        )

        return {
            "source_root_folder": str(self.source_root_folder),
            "source_root_changed": source_root_changed,
            "added": added,
            "removed": removed,
            "changed": changed,
            "current": current_index,
        }

    def lookup_copy(self, copy_name: str) -> str:
        """
        Méthode 3 : lookup de la copie.

        - prend en entrée un nom de copie
        - cherche dans l'index mémoïsé
        - si nécessaire, tente un rebuild automatique si le dossier source est connu
        - retourne le chemin si trouvé
        - sinon lève une exception
        """
        normalized_name = copy_name.strip().upper()

        if not self.index:
            self._ensure_index_loaded()

        if normalized_name in self.index:
            return self.index[normalized_name]

        raise CopyNotFoundError(f"Copy introuvable dans l'index : {normalized_name}")

    def warm_up(self) -> Dict[str, str]:
        """
        Assure qu'un index est disponible en mémoire.

        Priorité :
        1. index déjà chargé en mémoire
        2. index chargé depuis JSON
        3. rebuild depuis le dossier source connu
        """
        self._ensure_index_loaded()
        return self.index

    def _ensure_index_loaded(self) -> None:
        """
        Garantit qu'un index est chargé.
        """
        if self.index:
            return

        payload = self._load_saved_payload()
        saved_index = payload.get("index", {})
        saved_root = payload.get("source_root_folder")

        if saved_index:
            self.index = self._normalize_index(saved_index)

        if self.index:
            return

        if self.source_root_folder is None and saved_root:
            self.source_root_folder = Path(saved_root).resolve()

        if self.source_root_folder is not None:
            self.build_index(str(self.source_root_folder))
            return

        raise CopyLookupNotInitializedError(
            "Impossible de charger ou construire l'index : "
            "aucun index sauvegardé et aucun dossier source connu."
        )

    def _auto_load_from_disk(self) -> None:
        """
        Charge automatiquement la sauvegarde JSON au démarrage si elle existe.
        """
        payload = self._load_saved_payload()

        saved_root = payload.get("source_root_folder")
        saved_index = payload.get("index", {})

        if self.source_root_folder is None and saved_root:
            self.source_root_folder = Path(saved_root).resolve()

        if saved_index:
            self.index = self._normalize_index(saved_index)

    def _load_saved_payload(self) -> Dict[str, Any]:
        """
        Charge le JSON complet de sauvegarde.
        Retourne une structure vide si le fichier n'existe pas.
        """
        #print(f"Loading copy index from disk: {self.save_file}")
        if not self.save_file.exists():
            return {}

        try:
            with self.save_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise CopyLookupError(
                f"Le fichier de sauvegarde est invalide : {self.save_file}"
            ) from exc

        if not isinstance(data, dict):
            raise CopyLookupError(
                f"Le contenu du fichier de sauvegarde doit être un objet JSON : {self.save_file}"
            )

        source_root_folder = data.get("source_root_folder")
        index = data.get("index")

        if source_root_folder is not None and not isinstance(source_root_folder, str):
            raise CopyLookupError(
                f"'source_root_folder' doit être une chaîne dans {self.save_file}"
            )

        if index is not None and not isinstance(index, dict):
            raise CopyLookupError(
                f"'index' doit être un dictionnaire dans {self.save_file}"
            )

        return data

    def _save_payload(self, source_root_folder: str, index: Dict[str, str]) -> None:
        """
        Sauvegarde le dossier source et l'index dans le JSON.
        """
        self.save_file.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "source_root_folder": source_root_folder,
            "index": index,
        }

        with self.save_file.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _normalize_index(raw_index: Dict[str, str]) -> Dict[str, str]:
        """
        Normalise les clés en majuscules et vérifie les types.
        """
        normalized: Dict[str, str] = {}

        for key, value in raw_index.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise CopyLookupError(
                    "L'index sauvegardé contient des données invalides."
                )
            normalized[key.strip().upper()] = value

        return normalized
    


CopyLookup = _CopyLookup(root_folder=r"H:\github\cobol-documentor\datas\chatgpt", save_file="copy_index.json")
#print(CopyLookup.update_saved_index())