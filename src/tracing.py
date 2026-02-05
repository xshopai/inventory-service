"""
Unified OpenTelemetry tracing for Python services.

Supports multiple exporters based on OTEL_TRACES_EXPORTER environment variable:
- zipkin: Uses OTEL_EXPORTER_ZIPKIN_ENDPOINT
- otlp: Uses OTEL_EXPORTER_OTLP_ENDPOINT
- azure: Uses APPLICATIONINSIGHTS_CONNECTION_STRING
- none: Disables tracing

This module should be imported at the very beginning of the application,
before any other imports that might need instrumentation.
"""

import os
import logging

logger = logging.getLogger(__name__)

_tracing_initialized = False
_tracing_enabled = False


def setup_tracing(service_name: str = None) -> bool:
    """
    Configure tracing based on OTEL_TRACES_EXPORTER environment variable.
    
    Args:
        service_name: Service name for tracing (defaults to env vars)
        
    Returns:
        True if tracing was successfully configured, False otherwise
    """
    global _tracing_initialized, _tracing_enabled
    
    if _tracing_initialized:
        return _tracing_enabled
    
    _tracing_initialized = True
    
    exporter_type = os.environ.get('OTEL_TRACES_EXPORTER', 'none').lower()
    service_name = service_name or os.environ.get('OTEL_SERVICE_NAME', os.environ.get('SERVICE_NAME', 'unknown-service'))
    
    if exporter_type == 'zipkin':
        _tracing_enabled = _setup_zipkin(service_name)
    elif exporter_type == 'otlp':
        _tracing_enabled = _setup_otlp(service_name)
    elif exporter_type == 'azure':
        _tracing_enabled = _setup_azure(service_name)
    elif exporter_type == 'none':
        logger.info(f"ℹ️  Tracing disabled (OTEL_TRACES_EXPORTER={exporter_type})")
        _tracing_enabled = False
    else:
        logger.warning(f"⚠️  Unknown exporter type: {exporter_type}, tracing disabled")
        _tracing_enabled = False
    
    return _tracing_enabled


def _setup_zipkin(service_name: str) -> bool:
    """Configure Zipkin exporter."""
    try:
        endpoint = os.environ.get('OTEL_EXPORTER_ZIPKIN_ENDPOINT')
        if not endpoint:
            logger.warning("⚠️  Zipkin exporter selected but OTEL_EXPORTER_ZIPKIN_ENDPOINT not set")
            return False
        
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.zipkin.json import ZipkinExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        
        resource = Resource.create({
            "service.name": service_name,
            "service.instance.id": os.environ.get('HOSTNAME', 'localhost'),
        })
        
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        zipkin_exporter = ZipkinExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))
        
        RequestsInstrumentor().instrument()
        
        logger.info(f"✅ Tracing: Zipkin exporter → {endpoint}")
        return True
        
    except ImportError as e:
        logger.error(f"Zipkin exporter not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure Zipkin: {e}", exc_info=True)
        return False


def _setup_otlp(service_name: str) -> bool:
    """Configure OTLP exporter."""
    try:
        endpoint = os.environ.get('OTEL_EXPORTER_OTLP_ENDPOINT')
        if not endpoint:
            logger.warning("⚠️  OTLP exporter selected but OTEL_EXPORTER_OTLP_ENDPOINT not set")
            return False
        
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        
        resource = Resource.create({
            "service.name": service_name,
            "service.instance.id": os.environ.get('HOSTNAME', 'localhost'),
        })
        
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        otlp_exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        RequestsInstrumentor().instrument()
        
        logger.info(f"✅ Tracing: OTLP exporter → {endpoint}")
        return True
        
    except ImportError as e:
        logger.error(f"OTLP exporter not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure OTLP: {e}", exc_info=True)
        return False


def _setup_azure(service_name: str) -> bool:
    """Configure Azure Monitor exporter."""
    try:
        connection_string = os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING')
        if not connection_string:
            logger.warning("⚠️  Azure exporter selected but APPLICATIONINSIGHTS_CONNECTION_STRING not set")
            return False
        
        from azure.monitor.opentelemetry import configure_azure_monitor
        
        configure_azure_monitor(
            connection_string=connection_string,
            enable_live_metrics=True,
            logger_name=service_name,
            instrumentation_options={
                "azure_sdk": {"enabled": True},
                "flask": {"enabled": True},
                "requests": {"enabled": True},
                "sqlalchemy": {"enabled": True},
                "pymysql": {"enabled": True},
                "logging": {"enabled": True},
            },
        )
        
        logger.info(f"✅ Tracing: Azure Monitor configured for {service_name}")
        return True
        
    except ImportError as e:
        logger.error(f"Azure Monitor SDK not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure Azure Monitor: {e}", exc_info=True)
        return False


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled."""
    return _tracing_enabled
