"""
OutlineDocumentGenerator for converting domain models to Outline JSON format.

This domain service converts transformed content and assets to Outline's
JSON import format with proper collections, documents, and attachments.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import FolderStructure, OutlinePackage, TransformedContent
from .prosemirror_document_generator import ProseMirrorDocumentGenerator


class OutlineDocumentGenerator:
    """
    Domain service for converting transformed content to Outline JSON format.

    Converts domain models to the JSON structure expected by Outline's
    import system, including collections, documents, and attachments.
    """

    def __init__(self):
        """Initialize the generator with ProseMirror converter."""
        self._prosemirror_generator = ProseMirrorDocumentGenerator()

    def generate_outline_package(
        self, contents: List[TransformedContent], vault_name: str
    ) -> OutlinePackage:
        """
        Generate Outline package from transformed contents.

        Args:
            contents: List of transformed content from vault
            vault_name: Name of the vault/collection

        Returns:
            OutlinePackage ready for export
        """
        # Generate UUIDs for entities
        collection_id = str(uuid.uuid4())
        current_time = datetime.now().isoformat() + "Z"

        # Create metadata
        metadata = self._create_metadata(current_time)

        # First pass: Build document title to urlId mapping for wikilink resolution
        document_mapping = {}
        doc_ids = {}

        for content in contents:
            # Extract title from metadata or file path (same logic as _create_document)
            title = content.metadata.get("title")
            if not title:
                title = content.original_path.stem.replace("_", " ").replace("-", " ")
                title = " ".join(word.capitalize() for word in title.split())

            # Generate consistent doc_id and urlId
            doc_id = str(uuid.uuid4())
            url_id = self._generate_url_id(title)

            # Build mappings - include both the formatted title and the raw filename stem
            document_mapping[title] = url_id

            # Also map the raw filename stem (without .md) for direct filename matches
            filename_stem = content.original_path.stem
            if filename_stem != title:
                document_mapping[filename_stem] = url_id

            # Also map filename with spaces for common wikilink patterns like "document 1" -> "document1.md"
            filename_with_spaces = filename_stem.replace("-", " ").replace("_", " ")
            if filename_with_spaces != title and filename_with_spaces != filename_stem:
                document_mapping[filename_with_spaces] = url_id

            doc_ids[content.original_path] = doc_id

        # Initialize ProseMirror generator with document mapping for wikilink resolution
        self._prosemirror_generator = ProseMirrorDocumentGenerator(document_mapping)

        # Second pass: Process documents with wikilink resolution
        documents = {}
        attachments = {}
        document_structure = []
        all_warnings = []

        for content in contents:
            # Use pre-generated doc_id
            doc_id = doc_ids[content.original_path]
            document = self._create_document(content, doc_id, current_time)
            documents[doc_id] = document

            # Add to document structure
            structure_node = self._create_document_structure_node(
                content, doc_id, document["title"]
            )
            document_structure.append(structure_node)

            # Process assets
            for asset_path in content.assets:
                attachment_id = str(uuid.uuid4())
                attachment = self._create_attachment(asset_path, attachment_id, doc_id)
                attachments[attachment_id] = attachment

            # Collect warnings
            all_warnings.extend(content.warnings)

        # Create collection
        collection = self._create_collection(
            collection_id, vault_name, document_structure, current_time
        )

        return OutlinePackage(
            metadata=metadata,
            collections=[collection],
            documents=documents,
            attachments=attachments,
            warnings=all_warnings,
        )

    def generate_outline_package_with_folders(
        self,
        contents: List[TransformedContent],
        vault_name: str,
        folder_structure: Optional[FolderStructure] = None,
    ) -> OutlinePackage:
        """
        Generate Outline package preserving folder hierarchy as collections.

        Each folder becomes a separate Outline collection, with documents
        organized according to their folder location.

        Args:
            contents: List of transformed content from vault
            vault_name: Name of the vault
            folder_structure: Hierarchical folder structure from vault analysis

        Returns:
            OutlinePackage with multiple collections representing folders
        """
        # Fallback to flat structure if no folder structure provided
        if folder_structure is None:
            return self.generate_outline_package(contents, vault_name)

        current_time = datetime.now().isoformat() + "Z"
        metadata = self._create_metadata(current_time)

        # Build document mapping for wikilink resolution (same as flat structure)
        document_mapping = self._build_document_mapping(contents)
        self._prosemirror_generator = ProseMirrorDocumentGenerator(document_mapping)

        # Group contents by folder path
        contents_by_folder = self._group_contents_by_folder(contents, folder_structure)

        # Generate collections for each folder that has content
        collections = []
        all_documents = {}
        all_attachments = {}
        all_warnings = []

        for _folder_path, (folder, folder_contents) in contents_by_folder.items():
            if not folder_contents:  # Skip empty folders
                continue

            collection_id = str(uuid.uuid4())
            collection_name = folder.name if folder.name != "vault" else vault_name

            # Process documents for this folder
            documents, attachments, warnings = self._process_folder_contents(
                folder_contents, collection_id, current_time
            )

            # Create collection
            collection = self._create_folder_collection(
                collection_id, collection_name, documents, current_time
            )

            collections.append(collection)
            all_documents.update(documents)
            all_attachments.update(attachments)
            all_warnings.extend(warnings)

        return OutlinePackage(
            metadata=metadata,
            collections=collections,
            documents=all_documents,
            attachments=all_attachments,
            warnings=all_warnings,
        )

    def _build_document_mapping(
        self, contents: List[TransformedContent]
    ) -> Dict[str, str]:
        """Build document title to urlId mapping for wikilink resolution."""
        document_mapping = {}

        for content in contents:
            title = content.metadata.get("title")
            if not title:
                title = content.original_path.stem.replace("_", " ").replace("-", " ")
                title = " ".join(word.capitalize() for word in title.split())

            url_id = self._generate_url_id(title)
            document_mapping[title] = url_id

            # Also map filename variants
            filename_stem = content.original_path.stem
            if filename_stem != title:
                document_mapping[filename_stem] = url_id

            filename_with_spaces = filename_stem.replace("-", " ").replace("_", " ")
            if filename_with_spaces != title and filename_with_spaces != filename_stem:
                document_mapping[filename_with_spaces] = url_id

        return document_mapping

    def _group_contents_by_folder(
        self, contents: List[TransformedContent], folder_structure: FolderStructure
    ) -> Dict[Path, tuple[FolderStructure, List[TransformedContent]]]:
        """Group transformed contents by their containing folder path."""
        # Collect all folders in flat mapping (path -> folder)
        folders_by_path = {}

        def collect_folders(folder: FolderStructure) -> None:
            folders_by_path[folder.path] = folder
            for child in folder.child_folders:
                collect_folders(child)

        collect_folders(folder_structure)

        # Group contents by folder path
        contents_by_path = {path: [] for path in folders_by_path.keys()}

        for content in contents:
            # Find which folder contains this file
            file_parent = content.original_path.parent

            if file_parent in folders_by_path:
                contents_by_path[file_parent].append(content)
            else:
                # Fallback to root folder
                contents_by_path[folder_structure.path].append(content)

        # Return as (folder, contents) tuples
        return {
            path: (folders_by_path[path], contents_list)
            for path, contents_list in contents_by_path.items()
        }

    def _process_folder_contents(
        self, contents: List[TransformedContent], collection_id: str, current_time: str
    ) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], List[str]]:
        """Process contents for a single folder."""
        documents = {}
        attachments = {}
        warnings = []

        for content in contents:
            doc_id = str(uuid.uuid4())
            document = self._create_document(content, doc_id, current_time)
            documents[doc_id] = document

            # Process assets
            for asset_path in content.assets:
                attachment_id = str(uuid.uuid4())
                attachment = self._create_attachment(asset_path, attachment_id, doc_id)
                attachments[attachment_id] = attachment

            # Collect warnings
            warnings.extend(content.warnings)

        return documents, attachments, warnings

    def _create_folder_collection(
        self,
        collection_id: str,
        name: str,
        documents: Dict[str, Dict[str, Any]],
        current_time: str,
    ) -> Dict[str, Any]:
        """Create collection structure for a folder."""
        # Build document structure from documents
        document_structure = []
        for doc_id, document in documents.items():
            structure_node = {
                "id": doc_id,
                "url": f"/doc/{document['title'].lower().replace(' ', '-')}-{document['urlId']}",
                "title": document["title"],
                "children": [],  # Flat structure within collection
            }
            document_structure.append(structure_node)

        # Create empty ProseMirror document for collection description
        empty_doc = self._prosemirror_generator.convert_markdown("")

        # Truncate name to meet database constraints
        truncated_name = self._truncate_for_database(name, 100, "collection name")

        return {
            "id": collection_id,
            "urlId": self._generate_url_id(name),
            "name": truncated_name,
            "data": {"type": empty_doc.type, "content": empty_doc.content},
            "sort": {"field": "index", "direction": "asc"},
            "icon": None,
            "color": None,
            "permission": None,
            "documentStructure": document_structure,
        }

    def _create_metadata(self, current_time: str) -> Dict[str, Any]:
        """Create export metadata."""
        return {
            "exportVersion": 1,
            "version": "0.78.0-0",  # Outline version compatibility
            "createdAt": current_time,
            "createdById": str(uuid.uuid4()),  # Generated user ID
            "createdByEmail": "export@obsidian-exporter.local",
        }

    def _create_collection(
        self,
        collection_id: str,
        name: str,
        document_structure: List[Dict[str, Any]],
        current_time: str,
    ) -> Dict[str, Any]:
        """Create collection structure."""
        # Create empty ProseMirror document for collection description
        empty_doc = self._prosemirror_generator.convert_markdown("")

        # Truncate name to meet database constraints (100 chars max)
        truncated_name = self._truncate_for_database(name, 100, "collection name")

        return {
            "id": collection_id,
            "urlId": self._generate_url_id(name),  # Use original name for consistency
            "name": truncated_name,
            "data": {"type": empty_doc.type, "content": empty_doc.content},
            "sort": {"field": "index", "direction": "asc"},
            "icon": None,
            "color": None,
            "permission": None,
            "documentStructure": document_structure,
        }

    def _create_document(
        self, content: TransformedContent, doc_id: str, current_time: str
    ) -> Dict[str, Any]:
        """Create document structure."""
        # Extract title from metadata or file path
        title = content.metadata.get("title")
        if not title:
            title = content.original_path.stem.replace("_", " ").replace("-", " ")
            title = " ".join(word.capitalize() for word in title.split())

        # Truncate title to meet database constraints (100 chars max)
        truncated_title = self._truncate_for_database(title, 100, "document title")

        # Convert markdown to ProseMirror
        prosemirror_doc = self._prosemirror_generator.convert_markdown(content.markdown)

        return {
            "id": doc_id,
            "urlId": self._generate_url_id(title),  # Use original title for consistency
            "title": truncated_title,
            "icon": None,
            "color": None,
            "data": {"type": prosemirror_doc.type, "content": prosemirror_doc.content},
            "createdById": str(uuid.uuid4()),  # Generated user ID
            "createdByName": "Obsidian Exporter",
            "createdByEmail": "export@obsidian-exporter.local",
            "createdAt": current_time,
            "updatedAt": current_time,
            "publishedAt": current_time,
            "fullWidth": False,
            "template": False,
            "parentDocumentId": None,
        }

    def _create_document_structure_node(
        self, content: TransformedContent, doc_id: str, title: str
    ) -> Dict[str, Any]:
        """Create document structure node for navigation."""
        url_id = self._generate_url_id(title)

        return {
            "id": doc_id,
            "url": f"/doc/{title.lower().replace(' ', '-')}-{url_id}",
            "title": title,
            "children": [],  # Flat structure for now
        }

    def _create_attachment(
        self, asset_path: Path, attachment_id: str, document_id: str
    ) -> Dict[str, Any]:
        """Create attachment structure."""
        # Determine content type from file extension
        extension = asset_path.suffix.lower()
        content_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
            ".md": "text/markdown",
        }
        content_type = content_type_map.get(extension, "application/octet-stream")

        # Create upload key
        upload_key = f"uploads/{asset_path.name}"

        return {
            "id": attachment_id,
            "documentId": document_id,
            "contentType": content_type,
            "name": asset_path.name,
            "size": str(asset_path.stat().st_size if asset_path.exists() else 0),
            "key": upload_key,
        }

    def _generate_url_id(self, text: str) -> str:
        """Generate URL-friendly ID from text (exactly 10 characters)."""
        # Create a 10-character ID based on text hash for consistency
        import hashlib

        # Create consistent 10-character ID (Outline requirement)
        hash_obj = hashlib.md5(text.encode())
        return hash_obj.hexdigest()[:10]

    def _truncate_for_database(
        self, text: str, max_length: int, description: str = "text"
    ) -> str:
        """
        Truncate text to meet Outline's database constraints.

        Args:
            text: Text to truncate
            max_length: Maximum allowed length
            description: Description of what's being truncated (for logging)

        Returns:
            Truncated text that meets database constraints
        """
        if len(text) <= max_length:
            return text

        # Truncate to max_length, trying to break at word boundaries
        if max_length < 10:  # Too short to be meaningful
            return text[:max_length]

        # Try to break at a word boundary near the limit
        truncated = text[: max_length - 3]  # Leave room for "..."

        # Find last space to avoid breaking words
        last_space = truncated.rfind(" ")
        if last_space > max_length // 2:  # Only use space if it's not too early
            truncated = truncated[:last_space]

        return truncated + "..."
