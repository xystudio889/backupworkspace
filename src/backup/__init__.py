import re
import tarfile
from pathlib import Path, PurePath
from datetime import datetime, timezone
import hashlib
from os import makedirs

__all__ = ["BackupManager", "manager", "WILDCARD", "EXACT"]

__version__ = "0.2.0"

backup_path = Path.cwd() / ".xystudio" / "backup"

makedirs(backup_path, exist_ok=True)

WILDCARD = "wildcard"
EXACT = "exact"

class BackupManager:
    def __init__(self):
        self.exclude_rules = [
            (re.compile(r"^\..*"), "wildcard"),
            (re.compile("backup/**".replace("**", r".*?")), "wildcard"),
        ]
        self._validate_methods = {
            "exact": self._match_exact,
            "wildcard": self._match_wildcard,
        }

    def add_exclusion_rule(self, pattern: str, match_type: str = "wildcard"):
        pattern = pattern.replace("\\", "/").rstrip("/")

        self._validate_pattern(pattern)

        regex = self._pattern_to_regex(pattern)
        self.exclude_rules.append((re.compile(regex), match_type))

    def create_backup(self, backup_name: str, show_log=False):
        sanitized_name = self._sanitize_filename(backup_name)
        backup_dir = Path.cwd() / ".xystudio" / "backup"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")

        temp_file = backup_dir / f"{timestamp}-{sanitized_name}.tmp"

        with tarfile.open(temp_file, "w:gz") as tar:
            for file_path in self._walk_directory(Path.cwd()):
                if show_log:
                    print("adding ", file_path)
                rel_path = file_path.relative_to(Path.cwd())
                if not self._should_exclude(rel_path):
                    tar.add(file_path, arcname=str(rel_path))

        final_name = f"{timestamp}-{sanitized_name}.tar.gz"
        final_path = backup_dir / final_name
        temp_file.rename(final_path)
        return final_path

    def delete_backup(self, backup_name: str, index: int = None):
        backups = list(Path(".xystudio", "backup").glob("*.tar.gz"))
        matched = []

        for file in backups:
            name_part = "".join(file.stem.split("-")[-1].split(".")[:-1])
            if name_part == backup_name:
                matched.append(file)

        if not matched:
            raise ValueError(f"Backup not found: {backup_name}")

        matches = list(map(str, matched))
        final_match = []
        for i in matches:
            final_match.append(i[1:-7])

        if len(matched) > 1 and index is None:
            raise ValueError("Must specify index parameter\nAvailable options: " + ",".join(final_match))

        target = matched[index] if index is not None else matched[0]
        target.unlink()

    def extract_backup(self, backup_name: str, index: int = None):
        import subprocess

        backups = list(Path(".xystudio", "backup").glob("*.tar.gz"))
        matched = []

        for file in backups:
            name_part = "".join(file.stem.split("-")[-1].split(".")[:-1])
            if name_part == backup_name:
                matched.append(file)

        if not matched:
            raise ValueError(f"Backup not found: {backup_name}")

        matches = list(map(str, matched))
        final_match = []
        for i in matches:
            final_match.append(i[1:-7])

        if len(matched) > 1 and index is None:
            raise ValueError("Must specify index parameter\nAvailable options: " + ",".join(final_match))

        target = matched[index] if index is not None else matched[0]

        deep_path = Path(folder_name := str(target)[:-7])
        deep_path.mkdir(parents=True, exist_ok=True)

        cmd = ["tar", "-xzf", str(target), "-C", folder_name]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Unzip failed: {result.stderr}")
        else:
            print(f"Unzipped file is in ./{folder_name}")

    def _walk_directory(self, root: Path):
        for path in root.iterdir():
            rel_path = path.relative_to(root)
            if self._should_exclude(rel_path):
                continue

            if path.is_dir():
                yield from self._walk_directory(path)
            else:
                yield path

    def _should_exclude(self, rel_path: PurePath) -> bool:
        str_path = str(rel_path.as_posix())
        for pattern, match_type in self.exclude_rules:
            if self._validate_methods[match_type](str_path, pattern):
                return True
        return False

    def _match_exact(self, path: str, pattern: re.Pattern) -> bool:
        return bool(pattern.fullmatch(path))

    def _match_wildcard(self, path: str, pattern: re.Pattern) -> bool:
        return bool(pattern.search(path))

    def _validate_pattern(self, pattern: str):
        if "**" in pattern:
            if pattern.count("**") > 1:
                raise ValueError(f"Provided pattern contains more than one **: {pattern}")
            if not pattern.endswith("**"):
                raise ValueError(f"** must be at the end of the pattern: {pattern}")

            parts = pattern.split("/")
            if len(parts) > 1 and parts[-2] == "":
                raise ValueError(
                    f"The pattern cannot end with an empty segment: {pattern}"
                )
            return

        parts = pattern.split("/")
        for part in parts:
            if part.count("*") > 1:
                raise ValueError(f"The pattern contains more than one *: {pattern}")

    def _pattern_to_regex(self, pattern: str) -> str:
        regex = (
            pattern.replace(".", r"\.")
            .replace("*", r"[^/]*")
            .replace("**", r".*?")
        )

        if "**" in pattern:
            regex = f"^{regex}(/.*)?$"
        else:
            regex = f"^{regex}$"

        return regex

    def _sanitize_filename(self, name: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "_", name)

    def get_backup_hash(self, backup_name: str, index: int = None) -> str:
        """获取备份文件的 SHA256 哈希值"""
        backups = list(Path(".xystudio", "backup").glob("*.tar.gz"))
        matched = []
        for file in backups:
            name_part = "".join(file.stem.split("-")[-1].split(".")[:-1])
            print(name_part)
            if name_part == backup_name:
                matched.append(file)

        if not matched:
            raise ValueError(f"Backup not found: {backup_name}")

        if len(matched) > 1 and index is None:
            final_match = [f"{i}: {file.name}" for i, file in enumerate(matched)]
            raise ValueError("Must specify index parameter\nAvailable options:\n" + "\n".join(final_match))

        target = matched[index] if index is not None else matched[0]

        sha256_hash = hashlib.sha256()
        with open(target, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def verify_backup_hash(self, backup_name: str, expected_hash: str, index: int = None) -> bool:
        """验证备份文件的 SHA256 哈希"""
        actual_hash = self.get_backup_hash(backup_name, index)
        return actual_hash.lower() == expected_hash.lower()

def _write_exclude_rules(rules):
    import pickle

    with open(backup_path / "excludes.exc", "ab") as f:
        pickle.dump(rules, f)

def _read_exclude_rules():
    import pickle

    with open(backup_path / "excludes.exc", "rb") as f:
        exclude_rules = pickle.load(f)

    manager.exclude_rules = exclude_rules
    return exclude_rules

manager = BackupManager()

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Backup manager")
    subparsers = parser.add_subparsers(dest="command")

    manager.exclude_rules = _read_exclude_rules()

    create_parser = subparsers.add_parser("create", help="Create a backup")
    create_parser.add_argument("name", help="Name of the backup")

    delete_parser = subparsers.add_parser("delete", help="Delete a backup")
    delete_parser.add_argument("name", help="Name of the backup")
    delete_parser.add_argument("-i", "--index", type=int, help="Index of the backup to delete")

    extract_parser = subparsers.add_parser("extract", help="Extract a backup")
    extract_parser.add_argument("name", help="Name of the backup")
    extract_parser.add_argument("-i", "--index", type=int, help="Index of the backup to extract")

    verify_parser = subparsers.add_parser("verify", help="Verify a backup")
    verify_parser.add_argument("name", help="Name of the backup")
    verify_parser.add_argument("hash", help="Expected SHA256 hash of the backup")
    verify_parser.add_argument("-i", "--index", type=int, help="Index of the backup to verify")

    exclude_parser = subparsers.add_parser("exclude", help="Add an exclusion rule")
    exclude_parser.add_argument("pattern", help="Pattern to exclude")
    exclude_parser.add_argument(
        "-t", "--type", default="wildcard", choices=["exact", "wildcard"], help="Type of match"
    )

    get_hash_parser = subparsers.add_parser("get_hash", help="Get the SHA256 hash of a backup")
    get_hash_parser.add_argument("name", help="Name of the backup")
    get_hash_parser.add_argument("-i", "--index", type=int, help="Index of the backup to get the hash")

    args = parser.parse_args()

    if args.command == "create":
        backup_path = manager.create_backup(args.name)
        print(f"Backup created: {backup_path}")
    elif args.command == "delete":
        manager.delete_backup(args.name, args.index)
        print(f"Backup deleted: {args.name}")
    elif args.command == "extract":
        manager.extract_backup(args.name, args.index)
    elif args.command == "verify":
        if manager.verify_backup_hash(args.name, args.hash, args.index):
            print(f"Backup verified: {args.name}")
        else:
            print(f"Backup verification failed: {args.name}")
    elif args.command == "exclude":
        manager.add_exclusion_rule(args.pattern, args.type)
        _write_exclude_rules(manager.exclude_rules)
        print(f"Exclusion rule added: {args.pattern}")
    elif args.command == "get_hash":
        print(manager.get_backup_hash(args.name, args.index))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()