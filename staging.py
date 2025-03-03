import os
import re
import shutil
import sys
import tempfile

import pyzipper
import requests

from config import config


class Updater:
    def __init__(self, zip_path="update.zip"):
        self.zip_path = zip_path
        self.password = config.get('updater', 'zip_password').strip().encode()
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.backup_dir = os.path.join(self.project_dir, "backup")
        self.temp_extract_dir = tempfile.mkdtemp()
        self.version_file = os.path.join(self.project_dir, "version")
        github_repo = config.get('updater', 'github_repo')
        self.latest_release_url = f"https://api.github.com/repos/{github_repo}/releases/latest"
        self.EXCLUDED_ITEMS = config.get('updater', 'excluded_items')

    def get_current_version(self):
        """Read the current version from the version file."""
        if os.path.exists(self.version_file):
            with open(self.version_file, "r") as f:
                return f.read().strip()
        return "0.0.0"

    def _backup(self):
        """Create a backup of the current project, excluding specified items."""
        if os.path.exists(self.backup_dir):
            shutil.rmtree(self.backup_dir)
        os.makedirs(self.backup_dir)

        for item in os.listdir(self.project_dir):
            src_path = os.path.join(self.project_dir, item)
            dst_path = os.path.join(self.backup_dir, item)

            if item not in self.EXCLUDED_ITEMS:
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path)
                elif os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)

    def _extract(self):
        """Extract the password-protected ZIP file."""
        try:
            with pyzipper.AESZipFile(self.zip_path, 'r') as zip_ref:
                zip_ref.setpassword(self.password)
                zip_ref.extractall(self.temp_extract_dir)
        except RuntimeError as e:
            print("Error: Incorrect password or corrupted ZIP file.")
            print(e)
            return False
        return True

    def _replace_files(self):
        """Replace existing project files with the new ones from the extracted ZIP."""
        for item in os.listdir(self.temp_extract_dir):
            src_path = os.path.join(self.temp_extract_dir, item)
            dst_path = os.path.join(self.project_dir, item)

            if item not in self.EXCLUDED_ITEMS:
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                elif os.path.isfile(src_path):
                    shutil.copy2(src_path, dst_path)

    def _recover_data_files(self):
        # Restore `data/` folder

        data_folder = os.path.join(self.project_dir, "data")
        backup_data_folder = os.path.join(self.backup_dir, "data")

        if os.path.exists(backup_data_folder):
            if os.path.exists(data_folder):
                shutil.rmtree(data_folder)

            shutil.copytree(backup_data_folder, data_folder)
            print("Restored 'data/' folder.")

    def _clean_up(self):
        """Remove temporary extracted files."""
        shutil.rmtree(self.temp_extract_dir, ignore_errors=True)

    def update(self):
        """Perform the update process (backup, extract, replace, cleanup)."""
        print(f"Current version: {self.get_current_version()}")
        print("Starting update...")
        self._backup()

        if self._extract():
            print("Extraction successful, applying update...")
            self._replace_files()
            self._recover_data_files()
            self._clean_up()
            print("Update completed successfully.")
        else:
            print("Update failed due to extraction error.")

    def create_update_zip(self, output_dir="dist", bump="patch"):
        """Create 'update.zip' with an optional password, excluding EXCLUDED_ITEMS.
        Also bumps the version file.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        zip_path = os.path.join(output_dir, "update.zip")
        new_version = self._bump_version(bump)

        # Create a password-protected ZIP using AES encryption
        with pyzipper.AESZipFile(zip_path, 'w', compression=pyzipper.ZIP_LZMA, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(self.password)

            # Walk through the project directory and add files to the ZIP
            for root, dirs, files in os.walk(self.project_dir):
                # Remove excluded directories from traversal
                dirs[:] = [d for d in dirs if d not in self.EXCLUDED_ITEMS]

                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.project_dir)

                    # Exclude files in EXCLUDED_ITEMS
                    if any(exclude_item in file_path for exclude_item in self.EXCLUDED_ITEMS):
                        continue

                    # Write the file to the zip
                    zf.write(file_path, arcname)

        print(f"Update ZIP created: {zip_path} (version {new_version})")

    def _bump_version(self, bump="patch"):
        """Increment the version in the 'version' file (patch, minor, or major)."""
        version = self.get_current_version()

        if not re.match(r'^\d+\.\d+\.\d+$', version):
            print("Invalid version format. Defaulting to 1.0.0")
            version = "1.0.0"

        major, minor, patch = map(int, version.split("."))

        if bump == "major":
            major += 1
            minor, patch = 0, 0
        elif bump == "minor":
            minor += 1
            patch = 0
        else:  # Default to patch
            patch += 1

        new_version = f"{major}.{minor}.{patch}"

        # Write new version to version file
        with open(self.version_file, "w") as f:
            f.write(new_version)

        return new_version

    def restart_cli(self):
        """Restart the CLI tool."""
        print("Restarting application...")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def check_for_updates(self):
        """Check for a new update and apply if available."""
        current_version = self.get_current_version()
        latest_version, download_url = self._get_latest_version()

        if latest_version and latest_version != current_version:
            print(f"New version available: {latest_version} (Current: {current_version})")
            zip_path = self._download_update(download_url)

            if zip_path:
                self.zip_path = zip_path
                self.update()
                self.restart_cli()  # Uncomment if automatic restart is needed
            else:
                print("Update failed. Please try again.")
        else:
            print("You're using the latest version.")

    def _get_latest_version(self):
        """Fetch the latest release version from GitHub."""
        try:
            response = requests.get(self.latest_release_url)
            response.raise_for_status()
            data = response.json()
            return data["tag_name"], data["assets"][0]["browser_download_url"]
        except requests.RequestException:
            print("Failed to check for updates.")
            return None, None

    def _download_update(self, url):
        """Download the latest release ZIP."""
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "update.zip")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return zip_path
        except requests.RequestException:
            print("Failed to download update.")
            return None


if __name__ == "__main__":
    updater = Updater()
    updater.check_for_updates()
