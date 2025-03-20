#!/usr/bin/env python3
"""
Test script for template processing using docxtpl.

This module tests how to use the template processor to generate
a DOCX file from a template with variables extracted from text.
"""

import os
import sys
import pytest
from pathlib import Path
import argparse
import json
from docxtpl import DocxTemplate, RichText


@pytest.fixture
def sample_template():
    """Return the path to a sample template file."""
    template_path = os.path.join(os.getcwd(), "templates", "template.docx")
    if not os.path.exists(template_path):
        pytest.skip(f"Template file not found: {template_path}")
    return template_path


@pytest.fixture
def output_path():
    """Return a temporary output path for test files."""
    # Create a temporary output path in the tmp directory
    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    output_file = os.path.join(tmp_dir, "test_output.docx")
    
    # Yield the path for use in tests
    yield output_file
    
    # Clean up after tests
    if os.path.exists(output_file):
        os.remove(output_file)


@pytest.fixture
def sample_variables():
    """Return a dictionary of sample variables to use in the template."""
    return {
        "policy_number": "POL-123456789",
        "insured_name": "Mario Rossi",
        "incident_date": "15/03/2023",
        "damage_description": "Danni causati da infiltrazione d'acqua proveniente dal tetto.",
        "assessment_date": "22/03/2023",
        "claim_amount": "€ 5.750,00",
        "adjuster_name": "Luigi Bianchi",
        "report_date": "30/03/2023"
    }


def test_basic_template_processing(sample_template, output_path, sample_variables):
    """Test basic template processing with sample variables."""
    # Skip if no template is available
    if not os.path.exists(sample_template):
        pytest.skip(f"Template file not found: {sample_template}")
    
    # Load the template
    doc = DocxTemplate(sample_template)
    
    # Render the template with our variables
    doc.render(sample_variables)
    
    # Save the output
    doc.save(output_path)
    
    # Check that the output file was created
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0


def test_rich_text_formatting(sample_template, output_path, sample_variables):
    """Test template processing with rich text formatting."""
    # Skip if no template is available
    if not os.path.exists(sample_template):
        pytest.skip(f"Template file not found: {sample_template}")
    
    # Load the template
    doc = DocxTemplate(sample_template)
    
    # Create a rich text object
    rt = RichText()
    rt.add('Questo è un testo ', style='Normal')
    rt.add('in grassetto', bold=True)
    rt.add(' e questo è ', style='Normal')
    rt.add('in corsivo', italic=True)
    
    # Add the rich text to our variables
    variables = sample_variables.copy()
    variables['rich_text_example'] = rt
    
    # Render the template with our variables
    doc.render(variables)
    
    # Save the output
    doc.save(output_path)
    
    # Check that the output file was created
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0 