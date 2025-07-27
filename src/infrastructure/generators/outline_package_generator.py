"""
OutlinePackageGenerator for creating ZIP packages compatible with Outline import format.

This infrastructure component creates ZIP files containing JSON structures
and assets following the EXACT Outline export format.
"""

import json
import re
import zipfile
from pathlib import Path
from typing import Dict, Optional, Set

from ...domain.models import OutlinePackage


class OutlinePackageGenerator:
    """
    Infrastructure service for generating Outline-compatible ZIP packages.

    Creates ZIP files with the exact structure for Outline JSON import:
    - metadata.json with export metadata
    - Collection JSON files with documents and attachments
    - uploads/ directory with attachment files
    """

    def generate_package(
        self,
        package: OutlinePackage,
        output_path: Path,
        attachments_mapping: Optional[Dict[str, Path]] = None,
    ) -> Path:
        """
        Generate Outline ZIP package from package data.

        Args:
            package: OutlinePackage with metadata, collections, documents, attachments
            output_path: Path where ZIP file should be created
            attachments_mapping: Optional mapping of attachment IDs to file paths

        Returns:
            Path to the created ZIP file
        """
        if attachments_mapping is None:
            attachments_mapping = {}

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add metadata.json
            self._add_metadata_json(zf, package.metadata)

            # Add collection JSON files
            for collection in package.collections:
                self._add_collection_json(
                    zf, collection, package.documents, package.attachments
                )

            # Add attachment files to uploads/ directory
            self._add_attachments(zf, package.attachments, attachments_mapping)

        return output_path

    def validate_package(self, package_path: Path) -> bool:
        """
        Validate that generated package has correct Outline structure.

        Args:
            package_path: Path to ZIP package file

        Returns:
            True if package structure is valid for Outline import
        """
        if not zipfile.is_zipfile(package_path):
            return False

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                files = zf.namelist()

                # Must contain metadata.json
                if "metadata.json" not in files:
                    return False

                # Must contain at least one collection JSON file
                collection_files = [
                    f for f in files if f.endswith(".json") and f != "metadata.json"
                ]
                if not collection_files:
                    return False

                # Validate metadata.json structure
                try:
                    metadata = json.loads(zf.read("metadata.json"))
                    required_metadata_fields = ["exportVersion", "version", "createdAt"]
                    if not all(field in metadata for field in required_metadata_fields):
                        return False
                except json.JSONDecodeError:
                    return False

                # Validate collection JSON structures
                for collection_file in collection_files:
                    try:
                        collection_data = json.loads(zf.read(collection_file))
                        if "collection" not in collection_data:
                            return False
                        if "documents" not in collection_data:
                            return False
                        if "attachments" not in collection_data:
                            return False
                    except json.JSONDecodeError:
                        return False

                return True

        except (zipfile.BadZipFile, UnicodeDecodeError):
            return False

    def _add_metadata_json(self, zf: zipfile.ZipFile, metadata: Dict) -> None:
        """Add metadata.json to ZIP file."""
        metadata_json = json.dumps(metadata, indent=2)
        zf.writestr("metadata.json", metadata_json)

    def _add_collection_json(
        self,
        zf: zipfile.ZipFile,
        collection: Dict,
        documents: Dict[str, Dict],
        attachments: Dict[str, Dict],
    ) -> None:
        """Add collection JSON file to ZIP."""
        # Create safe filename from collection name
        safe_name = self._sanitize_filename(collection["name"])
        filename = f"{safe_name}.json"

        # Extract document IDs from collection's documentStructure
        collection_doc_ids = self._extract_document_ids(collection)

        # Filter documents to only include those in this collection
        collection_documents = {
            doc_id: doc_data
            for doc_id, doc_data in documents.items()
            if doc_id in collection_doc_ids
        }

        # Filter attachments to only include those belonging to collection documents
        collection_attachments = {
            att_id: att_data
            for att_id, att_data in attachments.items()
            if att_data.get("documentId") in collection_doc_ids
        }

        # Create collection JSON structure
        collection_data = {
            "collection": collection,
            "documents": collection_documents,  # Now filtered!
            "attachments": collection_attachments,  # Now filtered!
        }

        collection_json = json.dumps(collection_data, indent=2)
        zf.writestr(filename, collection_json)

    def _extract_document_ids(self, collection: Dict) -> Set[str]:
        """
        Recursively extract all document IDs from a collection's documentStructure.

        Handles nested document structures by traversing the 'children' property
        of each document node to ensure all nested documents are included.

        Args:
            collection: Collection dictionary containing documentStructure

        Returns:
            Set of all document IDs found in the structure (including nested ones)
        """
        doc_ids: Set[str] = set()

        # Handle missing or invalid documentStructure
        if "documentStructure" not in collection:
            return doc_ids

        document_structure = collection.get("documentStructure", [])
        if not isinstance(document_structure, list):
            return doc_ids

        # Define recursive function to traverse document nodes
        def extract_from_node(node: Dict) -> None:
            """Recursively extract IDs from a document node and its children."""
            if not isinstance(node, dict):
                return

            # Extract ID from current node
            node_id = node.get("id")
            if node_id:
                doc_ids.add(node_id)

            # Recursively process children
            children = node.get("children", [])
            if isinstance(children, list):
                for child in children:
                    extract_from_node(child)

        # Process all top-level document nodes
        for doc_node in document_structure:
            extract_from_node(doc_node)

        return doc_ids

    def _add_attachments(
        self,
        zf: zipfile.ZipFile,
        attachments: Dict[str, Dict],
        attachments_mapping: Dict[str, Path],
    ) -> None:
        """Add attachment files to uploads/ directory."""
        for attachment_id, attachment in attachments.items():
            # Get the upload key (path within ZIP)
            upload_key = attachment.get("key", f"uploads/{attachment['name']}")

            # Get the actual file path
            if attachment_id in attachments_mapping:
                file_path = attachments_mapping[attachment_id]
                if file_path.exists():
                    zf.write(file_path, upload_key)
                else:
                    # Create placeholder for missing file
                    zf.writestr(upload_key, f"Missing file: {file_path}")

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe use in ZIP file.

        Args:
            filename: Original filename

        Returns:
            Safe filename with problematic characters removed/replaced
        """
        # Replace problematic characters with underscores
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Remove any control characters
        safe_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", safe_name)

        # Limit length and strip whitespace
        safe_name = safe_name.strip()[:200]

        # Ensure it's not empty
        if not safe_name:
            safe_name = "Untitled"

        return safe_name
