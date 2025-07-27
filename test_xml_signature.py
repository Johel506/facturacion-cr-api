#!/usr/bin/env python3
"""
Simple test script for XML signature functionality.
"""
import sys
import os
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from utils.xml_signature import P12CertificateManager, XMLSignatureError

def test_certificate_validation():
    """Test certificate validation with dummy data."""
    print("Testing certificate validation...")
    
    # Create dummy P12 data (this would fail in real usage)
    dummy_p12_data = b"dummy certificate data"
    dummy_password = "dummy_password"
    
    try:
        # This should fail with dummy data
        cert_manager = P12CertificateManager(dummy_p12_data, dummy_password)
        print("✗ Certificate validation should have failed with dummy data")
        return False
    except XMLSignatureError as e:
        print(f"✓ Certificate validation correctly failed: {str(e)}")
        return True
    except Exception as e:
        print(f"✗ Unexpected error: {str(e)}")
        return False

def test_xml_signature_structure():
    """Test XML signature structure creation."""
    print("\nTesting XML signature structure...")
    
    # Test basic XML content
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica">
    <Clave>50612345678901234567890123456789012345678901234567890</Clave>
    <NumeroConsecutivo>00100001010000000001</NumeroConsecutivo>
    <FechaEmision>2025-01-01T00:00:00Z</FechaEmision>
</FacturaElectronica>"""
    
    try:
        from xml.etree.ElementTree import fromstring
        root = fromstring(xml_content)
        print("✓ XML parsing works correctly")
        
        # Test that we can create signature elements
        from xml.etree.ElementTree import Element, SubElement
        signature = Element("{http://www.w3.org/2000/09/xmldsig#}Signature")
        signature.set("Id", "test-signature")
        
        signed_info = SubElement(signature, "{http://www.w3.org/2000/09/xmldsig#}SignedInfo")
        print("✓ XML signature structure creation works")
        
        return True
        
    except Exception as e:
        print(f"✗ XML signature structure test failed: {str(e)}")
        return False

def test_xades_namespace():
    """Test XAdES namespace handling."""
    print("\nTesting XAdES namespace handling...")
    
    try:
        from utils.xml_signature import XAdESSignature
        
        # Check namespace constants
        if XAdESSignature.XADES_NS == "http://uri.etsi.org/01903/v1.3.2#":
            print("✓ XAdES namespace is correct")
        else:
            print("✗ XAdES namespace is incorrect")
            return False
            
        if XAdESSignature.XMLDSIG_NS == "http://www.w3.org/2000/09/xmldsig#":
            print("✓ XMLDSig namespace is correct")
        else:
            print("✗ XMLDSig namespace is incorrect")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ XAdES namespace test failed: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("Testing XML signature functionality...")
    print("=" * 60)
    
    tests = [
        test_certificate_validation,
        test_xml_signature_structure,
        test_xades_namespace
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())