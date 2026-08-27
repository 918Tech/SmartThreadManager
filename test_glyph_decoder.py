"""Tests for glyph decoder system."""

import pytest
from glyph_decoder import (
    GlyphDecoder,
    BrailleCodec,
    LLMGlyphDecoder,
    GlyphDecoderError,
    GlyphMetadata,
)


class TestBrailleCodec:
    """Test braille encoding/decoding."""
    
    def test_codec_initialization(self):
        codec = BrailleCodec()
        assert codec.logger is not None
        assert len(codec.pattern_map) > 0
    
    def test_encode_valid_pattern(self):
        codec = BrailleCodec()
        result = codec.encode_pattern(0b000001)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_encode_invalid_type(self):
        codec = BrailleCodec()
        with pytest.raises(GlyphDecoderError):
            codec.encode_pattern("not_an_int")
    
    def test_encode_out_of_range(self):
        codec = BrailleCodec()
        with pytest.raises(GlyphDecoderError):
            codec.encode_pattern(256)  # Out of range
    
    def test_encode_negative(self):
        codec = BrailleCodec()
        with pytest.raises(GlyphDecoderError):
            codec.encode_pattern(-1)
    
    def test_decode_valid_glyph(self):
        codec = BrailleCodec()
        # Decode a known braille character
        result = codec.decode_pattern('⠁')
        assert isinstance(result, int)
    
    def test_decode_invalid_type(self):
        codec = BrailleCodec()
        with pytest.raises(GlyphDecoderError):
            codec.decode_pattern(123)  # Not a string
    
    def test_decode_empty_string(self):
        codec = BrailleCodec()
        with pytest.raises(GlyphDecoderError):
            codec.decode_pattern("")


class TestGlyphDecoder:
    """Test glyph decoder functionality."""
    
    def test_decoder_initialization(self):
        decoder = GlyphDecoder()
        assert decoder.logger is not None
        assert decoder.codec is not None
        assert decoder.stats['decoded'] == 0
    
    def test_decode_single_glyph(self):
        decoder = GlyphDecoder()
        result = decoder.decode('⠁')
        assert isinstance(result, GlyphMetadata)
        assert result.glyph_id == '⠁'
        assert isinstance(result.braille_pattern, int)
    
    def test_decode_with_metadata(self):
        decoder = GlyphDecoder()
        metadata = {
            'semantic': 'test_meaning',
            'language': 'fr',
            'confidence': 0.95
        }
        result = decoder.decode('⠁', metadata=metadata)
        assert result.semantic_value == 'test_meaning'
        assert result.language == 'fr'
        assert result.confidence == 0.95
    
    def test_decode_invalid_input(self):
        decoder = GlyphDecoder()
        with pytest.raises(GlyphDecoderError):
            decoder.decode("")  # Empty string
    
    def test_decode_non_string_input(self):
        decoder = GlyphDecoder()
        with pytest.raises(GlyphDecoderError):
            decoder.decode(123)
    
    def test_cache_functionality(self):
        decoder = GlyphDecoder()
        # First decode
        result1 = decoder.decode('⠁')
        initial_decoded = decoder.stats['decoded']
        
        # Second decode (should use cache)
        result2 = decoder.decode('⠁')
        assert result1.glyph_id == result2.glyph_id
        assert decoder.stats['decoded'] == initial_decoded  # No additional decode
        assert decoder.stats['cached'] == 1
    
    def test_decode_sequence(self):
        decoder = GlyphDecoder()
        glyphs = '⠁⠂⠄'
        results = decoder.decode_sequence(glyphs)
        assert len(results) == 3
        assert all(isinstance(r, GlyphMetadata) for r in results)
    
    def test_decode_sequence_with_errors(self):
        decoder = GlyphDecoder()
        # Mix valid glyphs with test characters
        glyphs = '⠁A⠂'
        results = decoder.decode_sequence(glyphs)
        assert len(results) == 3  # All are decoded (even if some are invalid)
    
    def test_stats_tracking(self):
        decoder = GlyphDecoder()
        decoder.decode('⠁')
        decoder.decode('⠁')  # Cache hit
        stats = decoder.get_stats()
        assert stats['decoded'] == 1
        assert stats['cached'] == 1
        assert stats['failed'] == 0
    
    def test_clear_cache(self):
        decoder = GlyphDecoder()
        decoder.decode('⠁')
        assert len(decoder.cache) == 1
        decoder.clear_cache()
        assert len(decoder.cache) == 0


class TestLLMGlyphDecoder:
    """Test LLM glyph decoder functionality."""
    
    def test_llm_decoder_initialization(self):
        decoder = LLMGlyphDecoder()
        assert decoder.decoder is not None
        assert decoder.logger is not None
    
    def test_tokenize_simple_text(self):
        decoder = LLMGlyphDecoder()
        tokens = decoder.tokenize_glyphs('ABC')
        assert isinstance(tokens, list)
        assert len(tokens) == 3
        assert all(isinstance(t, int) for t in tokens)
    
    def test_tokenize_invalid_input(self):
        decoder = LLMGlyphDecoder()
        with pytest.raises(GlyphDecoderError):
            decoder.tokenize_glyphs(123)  # Not a string
    
    def test_tokenize_caching(self):
        decoder = LLMGlyphDecoder()
        tokens1 = decoder.tokenize_glyphs('test')
        tokens2 = decoder.tokenize_glyphs('test')
        assert tokens1 == tokens2
        assert 'test' in decoder.token_cache
    
    def test_detokenize_valid_tokens(self):
        decoder = LLMGlyphDecoder()
        tokens = [0b000001, 0b000010, 0b000100]
        text = decoder.detokenize_glyphs(tokens)
        assert isinstance(text, str)
        assert len(text) == 3
    
    def test_detokenize_invalid_input(self):
        decoder = LLMGlyphDecoder()
        with pytest.raises(GlyphDecoderError):
            decoder.detokenize_glyphs("not_a_list")
    
    def test_detokenize_invalid_token_type(self):
        decoder = LLMGlyphDecoder()
        with pytest.raises(GlyphDecoderError):
            decoder.detokenize_glyphs([1, "invalid", 3])
    
    def test_roundtrip_encoding(self):
        """Test that tokenize -> detokenize preserves information."""
        decoder = LLMGlyphDecoder()
        original = 'test'
        tokens = decoder.tokenize_glyphs(original)
        reconstructed = decoder.detokenize_glyphs(tokens)
        # Should have same length
        assert len(original) == len(reconstructed)
