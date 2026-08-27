"""Robust glyph decoder with comprehensive error handling and braille encoding."""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class GlyphDecoderError(Exception):
    """Base exception for glyph decoder errors."""
    pass


class BraillePattern(Enum):
    """Braille dot patterns for glyph encoding."""
    # Basic patterns for common glyphs
    DOT_1 = 0b000001
    DOT_2 = 0b000010
    DOT_3 = 0b000100
    DOT_4 = 0b001000
    DOT_5 = 0b010000
    DOT_6 = 0b100000
    DOT_7 = 0b1000000  # Extended for 7-dot patterns
    DOT_8 = 0b10000000  # Extended for 8-dot patterns


@dataclass
class GlyphMetadata:
    """Metadata for decoded glyphs."""
    glyph_id: str
    braille_pattern: int
    semantic_value: Optional[str] = None
    language: str = "en"
    confidence: float = 1.0
    original_encoding: Optional[bytes] = None


class BrailleCodec:
    """Codec for braille-based glyph encoding."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.pattern_map: Dict[int, str] = self._initialize_patterns()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for debugging."""
        logger = logging.getLogger('BrailleCodec')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_patterns(self) -> Dict[int, str]:
        """Initialize braille pattern to glyph mappings."""
        return {
            0b000001: '⠁',  # Dot 1
            0b000010: '⠂',  # Dot 2
            0b000100: '⠄',  # Dot 3
            0b001000: '⠈',  # Dot 4
            0b010000: '⠐',  # Dot 5
            0b100000: '⠠',  # Dot 6
            0b000011: '⠃',  # Dots 1-2
            0b000101: '⠅',  # Dots 1-3
            0b001001: '⠉',  # Dots 1-4
            0b010001: '⠑',  # Dots 1-5
            0b100001: '⠡',  # Dots 1-6
        }
    
    def encode_pattern(self, value: int) -> str:
        """Encode integer value to braille pattern."""
        if not isinstance(value, int):
            raise GlyphDecoderError(f"Expected int, got {type(value).__name__}")
        if value < 0 or value > 0xFF:
            raise GlyphDecoderError(f"Pattern value {value} out of range [0, 255]")
        
        try:
            result = self.pattern_map.get(value)
            if result is None:
                # Fallback: create pattern from dot positions
                result = self._construct_pattern(value)
            self.logger.debug(f"Encoded {value:08b} -> {result}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to encode pattern {value}: {e}")
            raise GlyphDecoderError(f"Pattern encoding failed: {e}") from e
    
    def decode_pattern(self, glyph: str) -> int:
        """Decode braille glyph to integer pattern."""
        if not isinstance(glyph, str):
            raise GlyphDecoderError(f"Expected str, got {type(glyph).__name__}")
        if len(glyph) == 0:
            raise GlyphDecoderError("Empty glyph string")
        
        try:
            # Reverse lookup in pattern map
            for pattern_value, pattern_glyph in self.pattern_map.items():
                if pattern_glyph == glyph[0]:
                    self.logger.debug(f"Decoded {glyph[0]} -> {pattern_value:08b}")
                    return pattern_value
            
            # Fallback: encode to UTF-8 and use first byte
            utf8_bytes = glyph[0].encode('utf-8')
            result = utf8_bytes[0] if utf8_bytes else 0
            self.logger.debug(f"Decoded {glyph[0]} (fallback) -> {result:08b}")
            return result
        except Exception as e:
            self.logger.error(f"Failed to decode glyph '{glyph}': {e}")
            raise GlyphDecoderError(f"Glyph decoding failed: {e}") from e
    
    def _construct_pattern(self, value: int) -> str:
        """Construct braille pattern from bit positions."""
        dots = []
        for i in range(6):
            if value & (1 << i):
                dots.append(i + 1)
        
        # Map dot positions to unicode braille
        if not dots:
            return '⠀'  # Empty pattern
        
        # Simplified: return unicode based on dot count
        return chr(0x2800 + value & 0xFF)


class GlyphDecoder:
    """Robust decoder for glyph-based semantic encoding."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or self._setup_logger()
        self.codec = BrailleCodec(logger=self.logger)
        self.cache: Dict[str, GlyphMetadata] = {}
        self.stats = {
            'decoded': 0,
            'failed': 0,
            'cached': 0
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for debugging."""
        logger = logging.getLogger('GlyphDecoder')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def decode(self, glyph: str, metadata: Optional[Dict] = None) -> GlyphMetadata:
        """Decode a single glyph with metadata."""
        if not isinstance(glyph, str) or len(glyph) == 0:
            raise GlyphDecoderError(f"Invalid glyph input: {glyph}")
        
        # Check cache
        if glyph in self.cache:
            self.logger.debug(f"Cache hit for glyph: {glyph}")
            self.stats['cached'] += 1
            return self.cache[glyph]
        
        try:
            pattern = self.codec.decode_pattern(glyph)
            
            glyph_meta = GlyphMetadata(
                glyph_id=glyph,
                braille_pattern=pattern,
                semantic_value=metadata.get('semantic') if metadata else None,
                language=metadata.get('language', 'en') if metadata else 'en',
                confidence=metadata.get('confidence', 1.0) if metadata else 1.0,
                original_encoding=glyph.encode('utf-8')
            )
            
            self.cache[glyph] = glyph_meta
            self.stats['decoded'] += 1
            self.logger.info(f"Decoded glyph: {glyph} (pattern: {pattern:08b})")
            return glyph_meta
        
        except Exception as e:
            self.stats['failed'] += 1
            self.logger.error(f"Failed to decode glyph '{glyph}': {e}")
            raise GlyphDecoderError(f"Glyph decode failed: {e}") from e
    
    def decode_sequence(self, glyphs: str) -> List[GlyphMetadata]:
        """Decode a sequence of glyphs."""
        if not isinstance(glyphs, str):
            raise GlyphDecoderError(f"Expected string, got {type(glyphs).__name__}")
        
        results = []
        errors = []
        
        for idx, glyph in enumerate(glyphs):
            try:
                result = self.decode(glyph)
                results.append(result)
            except GlyphDecoderError as e:
                errors.append((idx, glyph, str(e)))
                self.logger.warning(f"Error at position {idx}: {e}")
        
        if errors:
            self.logger.warning(f"Decoded {len(results)} glyphs with {len(errors)} errors")
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """Get decoding statistics."""
        return self.stats.copy()
    
    def clear_cache(self) -> None:
        """Clear the glyph cache."""
        cache_size = len(self.cache)
        self.cache.clear()
        self.logger.info(f"Cleared cache ({cache_size} entries)")


class LLMGlyphDecoder:
    """Embedded LLM decoder for tiny language models."""
    
    def __init__(self, model_config: Optional[Dict] = None):
        self.model_config = model_config or {}
        self.logger = self._setup_logger()
        self.decoder = GlyphDecoder(logger=self.logger)
        self.token_cache: Dict[str, List[int]] = {}
    
    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('LLMGlyphDecoder')
        logger.setLevel(logging.INFO)
        return logger
    
    def tokenize_glyphs(self, text: str) -> List[int]:
        """Convert text to glyph tokens."""
        if not isinstance(text, str):
            raise GlyphDecoderError("Input must be string")
        
        if text in self.token_cache:
            self.logger.debug(f"Token cache hit: {text}")
            return self.token_cache[text]
        
        try:
            tokens = []
            for char in text:
                # Map character to glyph pattern
                glyph_meta = self.decoder.decode(char)
                tokens.append(glyph_meta.braille_pattern)
            
            self.token_cache[text] = tokens
            return tokens
        except Exception as e:
            self.logger.error(f"Tokenization failed: {e}")
            raise GlyphDecoderError(f"Tokenization failed: {e}") from e
    
    def detokenize_glyphs(self, tokens: List[int]) -> str:
        """Convert glyph tokens back to text."""
        if not isinstance(tokens, list):
            raise GlyphDecoderError("Tokens must be a list")
        
        try:
            text = ""
            for token in tokens:
                if not isinstance(token, int):
                    raise GlyphDecoderError(f"Token must be int, got {type(token).__name__}")
                glyph = self.decoder.codec.encode_pattern(token)
                text += glyph
            return text
        except Exception as e:
            self.logger.error(f"Detokenization failed: {e}")
            raise GlyphDecoderError(f"Detokenization failed: {e}") from e
