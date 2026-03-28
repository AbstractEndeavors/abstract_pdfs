"""
PDF to images converter with explicit configuration and schema validation.

This module prioritizes:
- Explicit environment wiring (no magic defaults)
- Schema-based configuration (pydantic)
- Queue-friendly design (generators for streaming)
- No global state or callbacks
"""

from pathlib import Path
from typing import Generator, Optional
from dataclasses import dataclass
from enum import Enum
import tempfile

from pydantic import BaseModel, Field, field_validator
from PIL.Image import Image


class ImageFormat(str, Enum):
    """Supported output image formats."""
    PNG = "png"
    JPEG = "jpeg"
    PPM = "ppm"  # Fast, uncompressed


class ConversionConfig(BaseModel):
    """Schema for PDF-to-image conversion parameters."""
    
    dpi: int = Field(
        default=600,
        ge=72,
        le=600,
        description="Resolution in dots per inch. Higher = better quality, larger files."
    )
    fmt: ImageFormat = Field(
        default=ImageFormat.PNG,
        description="Output image format"
    )
    first_page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Convert only from this page onwards (1-indexed, None = start from page 1)"
    )
    last_page: Optional[int] = Field(
        default=None,
        ge=1,
        description="Convert up to and including this page (1-indexed, None = convert all)"
    )
    
    @field_validator('last_page')
    @classmethod
    def last_page_after_first(cls, v, info):
        if v is not None and info.data.get('first_page') is not None:
            if v < info.data['first_page']:
                raise ValueError('last_page must be >= first_page')
        return v


class PDFToImagesRegistry:
    """
    Registry-based converter (no globals, explicit dependency injection).
    
    Manages conversion lifecycle with explicit configuration wiring.
    """
    
    def __init__(self, config: Optional[ConversionConfig] = None):
        """
        Initialize converter with explicit configuration.
        
        Args:
            config: ConversionConfig instance. If None, uses defaults.
        """
        self.config = config or ConversionConfig()
    
    def convert(
        self,
        pdf_path: str | Path,
    ) -> Generator[tuple[int, Image], None, None]:
        """
        Convert PDF pages to images, yielding (page_number, image) tuples.
        
        Generator design allows processing large PDFs without loading all
        pages into memory. Queue-friendly: results can be enqueued as they arrive.
        
        Args:
            pdf_path: Path to PDF file
            
        Yields:
            (page_number, PIL.Image) tuples where page_number is 1-indexed
            
        Raises:
            FileNotFoundError: If PDF doesn't exist
            ValueError: If conversion fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise ImportError(
                "pdf2image not installed. Install with: pip install pdf2image"
            )
        
        # Prepare page range (pdf2image uses 1-indexed pages)
        first_page = self.config.first_page or 1
        last_page = self.config.last_page
        
        try:
            images = convert_from_path(
                str(pdf_path),
                dpi=self.config.dpi,
                fmt=self.config.fmt.value,
                first_page=first_page,
                last_page=last_page,
            )
        except Exception as e:
            raise ValueError(f"Failed to convert PDF: {e}") from e
        
        # Yield with 1-indexed page numbers
        for i, image in enumerate(images, start=first_page):
            yield (i, image)
    
    def convert_to_files(
        self,
        pdf_path: str | Path,
        output_dir: str | Path,
        filename_template: str = "page_{page_num:04d}.{ext}",
    ) -> list[Path]:
        """
        Convert PDF pages and save to disk.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images
            filename_template: Template for output filenames.
                Available variables: {page_num}, {ext}
                
        Returns:
            List of saved image paths in order
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        ext = self.config.fmt.value
        saved_paths = []
        
        for page_num, image in self.convert(pdf_path):
            filename = filename_template.format(page_num=page_num, ext=ext)
            output_path = output_dir / filename
            
            image.save(output_path, format=self.config.fmt.value.upper())
            saved_paths.append(output_path)
        
        return saved_paths


# Convenience function for simple use cases
def pdf_to_images(
    pdf_path: str | Path,
    dpi: int = 600,
    fmt: str = "png",
    first_page: Optional[int] = None,
    last_page: Optional[int] = None,
) -> Generator[tuple[int, Image], None, None]:
    """
    Quick converter for one-off conversions.
    
    For production code, use PDFToImagesRegistry directly for explicit
    configuration management.
    
    Args:
        pdf_path: Path to PDF
        dpi: Resolution (72-600)
        fmt: Output format ("png", "jpeg", "ppm")
        first_page: Start from this page (1-indexed)
        last_page: End at this page (1-indexed)
        
    Yields:
        (page_number, PIL.Image) tuples
    """
    config = ConversionConfig(
        dpi=dpi,
        fmt=ImageFormat(fmt),
        first_page=first_page,
        last_page=last_page,
    )
    converter = PDFToImagesRegistry(config)
    yield from converter.convert(pdf_path)


