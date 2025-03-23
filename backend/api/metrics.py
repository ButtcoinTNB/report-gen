"""
Metrics API endpoints for monitoring system performance
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, List, Optional
import logging
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from utils.metrics import MetricsCollector
from services.docx_formatter import docx_formatter
from ..utils.resource_manager import resource_manager

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Create metrics collector instance
metrics_file = Path(__file__).parent.parent / "data" / "metrics.json"
metrics_collector = MetricsCollector(metrics_file=metrics_file)

@router.get("/metrics/summary", response_model=Dict[str, Any])
async def get_metrics_summary():
    """
    Get a summary of performance metrics
    """
    try:
        # Get document generation metrics
        docx_metrics = docx_formatter.get_metrics()
        
        # Get report generation metrics from the collector
        report_metrics = metrics_collector.get_metrics("report_generation", limit=100)
        error_metrics = metrics_collector.get_metrics("report_generation_error", limit=20)
        
        # Calculate statistics from report metrics
        total_reports = len(report_metrics)
        avg_generation_time = 0
        avg_quality_score = 0
        avg_iterations = 0
        
        if total_reports > 0:
            # Calculate averages
            avg_generation_time = sum(m.get("duration", 0) for m in report_metrics) / total_reports
            avg_quality_score = sum(m.get("quality_score", 0) for m in report_metrics) / total_reports
            avg_iterations = sum(m.get("iterations", 0) for m in report_metrics) / total_reports
        
        # Get resource metrics
        resource_count = sum(len(resources) for resources in resource_manager.resources.values())
        
        # Build the summary
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "document_generation": {
                "total_documents": docx_metrics.get("total_documents", 0),
                "avg_generation_time": docx_metrics.get("avg_generation_time", 0),
                "cache_hits": docx_metrics.get("cache_hits", 0),
                "cache_misses": docx_metrics.get("cache_misses", 0),
                "quality_check_failures": docx_metrics.get("quality_check_failures", 0),
                "cache_hit_ratio": (
                    docx_metrics.get("cache_hits", 0) / 
                    max(1, (docx_metrics.get("cache_hits", 0) + docx_metrics.get("cache_misses", 0)))
                )
            },
            "report_generation": {
                "total_reports": total_reports,
                "total_errors": len(error_metrics),
                "avg_generation_time": avg_generation_time,
                "avg_quality_score": avg_quality_score,
                "avg_iterations": avg_iterations,
                "error_rate": len(error_metrics) / max(1, total_reports + len(error_metrics))
            },
            "resources": {
                "total_tracked": resource_count,
                "by_type": {
                    res_type: len(resources) 
                    for res_type, resources in resource_manager.resources.items()
                }
            },
            "system": {
                "uptime": time.time() - metrics_collector.get_metrics("system_startup", limit=1)[0].get("timestamp", time.time()) 
                if metrics_collector.get_metrics("system_startup", limit=1) else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating metrics summary: {str(e)}"
        )

@router.get("/metrics/documents", response_model=Dict[str, Any])
async def get_document_metrics(limit: int = Query(10, ge=1, le=100)):
    """
    Get detailed metrics about document generation
    """
    try:
        # Get document metrics from formatter
        docx_metrics = docx_formatter.get_metrics()
        
        # Get detailed metrics about recent documents
        recent_docs = metrics_collector.get_metrics("document_generation", limit=limit)
        
        return {
            "status": "success",
            "summary": docx_metrics,
            "recent_documents": recent_docs
        }
    except Exception as e:
        logger.error(f"Error getting document metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating document metrics: {str(e)}"
        )

@router.get("/metrics/reports", response_model=Dict[str, Any])
async def get_report_metrics(limit: int = Query(10, ge=1, le=100)):
    """
    Get detailed metrics about report generation
    """
    try:
        # Get report metrics
        report_metrics = metrics_collector.get_metrics("report_generation", limit=limit)
        error_metrics = metrics_collector.get_metrics("report_generation_error", limit=limit)
        
        # Calculate summary statistics
        total_reports = len(metrics_collector.get_metrics("report_generation"))
        total_errors = len(metrics_collector.get_metrics("report_generation_error"))
        
        # Calculate averages if we have data
        if report_metrics:
            avg_generation_time = sum(m.get("duration", 0) for m in report_metrics) / len(report_metrics)
            avg_quality_score = sum(m.get("quality_score", 0) for m in report_metrics) / len(report_metrics)
            avg_iterations = sum(m.get("iterations", 0) for m in report_metrics) / len(report_metrics)
        else:
            avg_generation_time = 0
            avg_quality_score = 0
            avg_iterations = 0
        
        return {
            "status": "success",
            "summary": {
                "total_reports": total_reports,
                "total_errors": total_errors,
                "error_rate": total_errors / max(1, total_reports + total_errors),
                "avg_generation_time": avg_generation_time,
                "avg_quality_score": avg_quality_score,
                "avg_iterations": avg_iterations
            },
            "recent_reports": report_metrics,
            "recent_errors": error_metrics
        }
    except Exception as e:
        logger.error(f"Error getting report metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating report metrics: {str(e)}"
        )

@router.post("/metrics/record-startup")
async def record_startup():
    """
    Record a system startup event (for uptime tracking)
    """
    try:
        # Record startup time
        metrics_collector.add_metric("system_startup", {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat()
        })
        
        return {"status": "success", "message": "Startup recorded successfully"}
    except Exception as e:
        logger.error(f"Error recording startup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error recording startup: {str(e)}"
        ) 