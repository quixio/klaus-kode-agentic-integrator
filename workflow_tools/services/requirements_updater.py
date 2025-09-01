# requirements_updater.py - Service for updating requirements.txt with latest versions

import re
import requests
from typing import Optional, Tuple
from workflow_tools.common import printer


class RequirementsUpdater:
    """Service for updating package versions in requirements.txt files."""
    
    @staticmethod
    def fetch_latest_quixstreams_version() -> Optional[str]:
        """
        Fetch the latest quixstreams version from PyPI.
        
        Returns:
            The latest version string (e.g., "3.22.0") or None if fetch fails
        """
        try:
            response = requests.get("https://pypi.org/pypi/quixstreams/json", timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("info", {}).get("version")
                if latest_version:
                    printer.print_debug(f"📦 Latest quixstreams version from PyPI: {latest_version}")
                    return latest_version
                else:
                    printer.print_debug("⚠️ Could not parse version from PyPI response")
                    return None
            else:
                printer.print_debug(f"⚠️ Failed to fetch from PyPI: HTTP {response.status_code}")
                return None
        except requests.RequestException as e:
            printer.print_debug(f"⚠️ Error fetching latest quixstreams version: {e}")
            return None
        except Exception as e:
            printer.print_debug(f"⚠️ Unexpected error fetching quixstreams version: {e}")
            return None
    
    @staticmethod
    def parse_requirement_line(line: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Parse a requirement line to extract package name, extras, operator, and version.
        
        Args:
            line: A requirement line (e.g., "quixstreams[s3]==3.17.0" or "quixstreams>=3.17")
            
        Returns:
            Tuple of (package_name, extras, operator, version) or (None, None, None, None) if not parseable
        """
        # Match patterns like: package[extra]==1.2.3, package[extra1,extra2]>=1.2, etc.
        pattern = r'^([a-zA-Z0-9\-_]+)(\[[a-zA-Z0-9\-_,]+\])?\s*([><=~!]+)\s*([\d.]+(?:\.\*)?)'
        match = re.match(pattern, line.strip())
        
        if match:
            package_name = match.group(1)
            extras = match.group(2) or ""  # Will be "[s3]" or "" if no extras
            operator = match.group(3)
            version = match.group(4)
            return package_name, extras, operator, version
        
        # Check if it's just a package name without version (with or without extras)
        simple_pattern = r'^([a-zA-Z0-9\-_]+)(\[[a-zA-Z0-9\-_,]+\])?\s*$'
        simple_match = re.match(simple_pattern, line.strip())
        if simple_match:
            package_name = simple_match.group(1)
            extras = simple_match.group(2) or ""
            return package_name, extras, None, None
            
        return None, None, None, None
    
    @staticmethod
    def update_quixstreams_in_requirements(requirements_content: str, latest_version: Optional[str] = None) -> Tuple[str, bool]:
        """
        Update quixstreams version in requirements.txt content.
        
        Args:
            requirements_content: The content of requirements.txt file
            latest_version: The latest version to use (if None, will fetch from PyPI)
            
        Returns:
            Tuple of (updated_content, was_updated) where was_updated indicates if changes were made
        """
        if latest_version is None:
            latest_version = RequirementsUpdater.fetch_latest_quixstreams_version()
            if latest_version is None:
                printer.print_debug("⚠️ Could not fetch latest quixstreams version, skipping update")
                return requirements_content, False
        
        lines = requirements_content.split('\n')
        updated_lines = []
        was_updated = False
        quixstreams_found = False
        
        for line in lines:
            # Skip comments and empty lines
            if line.strip().startswith('#') or not line.strip():
                updated_lines.append(line)
                continue
            
            package_name, extras, operator, version = RequirementsUpdater.parse_requirement_line(line)
            
            if package_name and package_name.lower() == 'quixstreams':
                if not quixstreams_found:
                    # This is the first quixstreams line - process it
                    quixstreams_found = True
                    
                    # Check if version needs updating
                    if version and version != latest_version:
                        # Preserve the operator style if it exists, otherwise use ==
                        if operator:
                            if operator in ['>=', '>', '~=']:
                                # For these operators, we can safely update to latest
                                new_line = f"quixstreams{extras}{operator}{latest_version}"
                            elif operator in ['==', '<=', '<']:
                                # For exact or upper bounds, update to exact latest version
                                new_line = f"quixstreams{extras}=={latest_version}"
                            else:
                                # For any other operator, default to exact version
                                new_line = f"quixstreams{extras}=={latest_version}"
                        else:
                            new_line = f"quixstreams{extras}=={latest_version}"
                        
                        extras_display = f" with {extras}" if extras else ""
                        printer.print(f"📦 Updating quixstreams{extras_display} from {operator}{version} to =={latest_version}")
                        updated_lines.append(new_line)
                        was_updated = True
                    elif not version:
                        # No version specified, add the latest version
                        new_line = f"quixstreams{extras}=={latest_version}"
                        extras_display = f" with {extras}" if extras else ""
                        printer.print(f"📦 Adding version to quixstreams{extras_display}: =={latest_version}")
                        updated_lines.append(new_line)
                        was_updated = True
                    else:
                        # Version is already latest
                        updated_lines.append(line)
                else:
                    # This is a duplicate quixstreams line - skip it
                    printer.print(f"📦 Removing duplicate quixstreams line: {line.strip()}")
                    was_updated = True
            else:
                updated_lines.append(line)
        
        # If quixstreams wasn't found at all, add it
        if not quixstreams_found:
            printer.print(f"📦 Adding quixstreams=={latest_version} to requirements")
            # Find a good place to insert it (after other packages, before comments at end)
            insert_index = len(updated_lines)
            for i in range(len(updated_lines) - 1, -1, -1):
                if updated_lines[i].strip() and not updated_lines[i].strip().startswith('#'):
                    insert_index = i + 1
                    break
            updated_lines.insert(insert_index, f"quixstreams=={latest_version}")
            was_updated = True
        
        return '\n'.join(updated_lines), was_updated
    
    @staticmethod
    def update_requirements_file(file_path: str, latest_version: Optional[str] = None) -> bool:
        """
        Update quixstreams version in a requirements.txt file.
        
        Args:
            file_path: Path to the requirements.txt file
            latest_version: The latest version to use (if None, will fetch from PyPI)
            
        Returns:
            True if file was updated, False otherwise
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated_content, was_updated = RequirementsUpdater.update_quixstreams_in_requirements(content, latest_version)
            
            if was_updated:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                printer.print(f"✅ Updated requirements.txt with latest quixstreams version")
                return True
            else:
                printer.print("ℹ️ No quixstreams version update needed")
                return False
                
        except FileNotFoundError:
            printer.print_debug(f"⚠️ Requirements file not found: {file_path}")
            return False
        except Exception as e:
            printer.print_debug(f"⚠️ Error updating requirements file: {e}")
            return False