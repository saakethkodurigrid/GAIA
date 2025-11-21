"""
Parser for Excalidraw canvas JSON to extract graph structure and metrics
"""
from typing import Dict, List, Any, Set
import json


class CanvasParser:
    """Parses Excalidraw JSON to extract components, edges, and annotations"""
    
    def parse(self, canvas_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Excalidraw JSON and extract:
        - Component count (nodes)
        - Edge count (connections)
        - Component types (service, storage, infra, external)
        - Annotations (replicas, region, scale)
        - Graph structure
        """
        elements = canvas_json.get("elements", [])
        
        # Extract nodes (rectangles, ellipses, diamonds)
        nodes = []
        edges = []
        labels = {}
        text_elements = []
        
        # First pass: collect all elements
        for elem in elements:
            elem_type = elem.get("type", "")
            
            if elem_type in ["rectangle", "ellipse", "diamond"]:
                # This is a component
                node_id = elem.get("id", "")
                nodes.append({
                    "id": node_id,
                    "type": elem_type,
                    "x": elem.get("x", 0),
                    "y": elem.get("y", 0),
                    "width": elem.get("width", 0),
                    "height": elem.get("height", 0)
                })
            
            elif elem_type == "arrow":
                # This is a connection/edge
                start_binding = elem.get("startBinding") or {}
                end_binding = elem.get("endBinding") or {}
                start_id = start_binding.get("elementId") if isinstance(start_binding, dict) else None
                end_id = end_binding.get("elementId") if isinstance(end_binding, dict) else None
                arrow_label = ""
                
                # Check for text elements near the arrow (labels)
                arrow_x = elem.get("x", 0)
                arrow_y = elem.get("y", 0)
                
                if start_id and end_id:
                    edges.append({
                        "from": start_id,
                        "to": end_id,
                        "label": arrow_label,
                        "points": elem.get("points", [])
                    })
            
            elif elem_type == "text":
                text_content = elem.get("text", "")
                container_id = elem.get("containerId")
                
                # Store text element for later matching
                text_elements.append({
                    "id": elem.get("id", ""),
                    "text": text_content,
                    "x": elem.get("x", 0),
                    "y": elem.get("y", 0),
                    "containerId": container_id
                })
                
                # If bound to a container, it's a label
                if container_id:
                    labels[container_id] = text_content
        
        # Second pass: match text elements to nearby nodes (for labels)
        for text_elem in text_elements:
            if text_elem.get("containerId"):
                continue  # Already handled
            
            text_x = text_elem["x"]
            text_y = text_elem["y"]
            text_content = text_elem["text"]
            
            # Find nearest node (within reasonable distance)
            for node in nodes:
                node_x = node["x"]
                node_y = node["y"]
                node_width = node["width"]
                node_height = node["height"]
                
                # Check if text is inside or very close to the node
                if (node_x <= text_x <= node_x + node_width and
                    node_y <= text_y <= node_y + node_height):
                    labels[node["id"]] = text_content
                    break
        
        # Extract component types from labels
        component_types = self._extract_component_types(nodes, labels)
        annotations = self._extract_annotations(labels)
        
        return {
            "component_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
            "labels": labels,
            "component_types": component_types,
            "annotations": annotations,
            "timestamp": None  # Could add timestamp parsing
        }
    
    def _extract_component_types(self, nodes: List[Dict], labels: Dict[str, str]) -> Dict[str, str]:
        """Extract component type (service, storage, infra, external) from labels"""
        type_keywords = {
            "service": ["api", "service", "microservice", "backend", "frontend"],
            "storage": ["db", "database", "cache", "redis", "postgres", "mysql", "storage"],
            "infra": ["load balancer", "lb", "gateway", "queue", "kafka", "cdn"],
            "external": ["client", "user", "external", "third-party"]
        }
        
        component_types = {}
        for node in nodes:
            node_id = node["id"]
            label = labels.get(node_id, "").lower()
            
            detected_type = "service"  # default
            for comp_type, keywords in type_keywords.items():
                if any(keyword in label for keyword in keywords):
                    detected_type = comp_type
                    break
            
            component_types[node_id] = detected_type
        
        return component_types
    
    def _extract_annotations(self, labels: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """Extract annotations like replicas, region, scale from labels"""
        annotations = {}
        
        for node_id, label in labels.items():
            annot = {}
            
            # Look for replicas
            if "replica" in label.lower():
                import re
                replica_match = re.search(r'replica[s]?\s*[=:]?\s*(\d+)', label, re.IGNORECASE)
                if replica_match:
                    annot["replicas"] = int(replica_match.group(1))
            
            # Look for region
            if "region" in label.lower():
                import re
                region_match = re.search(r'region[s]?\s*[=:]?\s*([a-z0-9-]+)', label, re.IGNORECASE)
                if region_match:
                    annot["region"] = region_match.group(1)
            
            # Look for scale
            if "scale" in label.lower():
                import re
                scale_match = re.search(r'scale[s]?\s*[=:]?\s*(\d+)', label, re.IGNORECASE)
                if scale_match:
                    annot["scale"] = int(scale_match.group(1))
            
            if annot:
                annotations[node_id] = annot
        
        return annotations
    
    def get_graph_summary(self, parsed_data: Dict[str, Any]) -> str:
        """Generate a text summary of the graph structure"""
        nodes = parsed_data["nodes"]
        edges = parsed_data["edges"]
        component_types = parsed_data["component_types"]
        labels = parsed_data["labels"]
        annotations = parsed_data["annotations"]
        
        summary_parts = [
            f"Canvas contains {len(nodes)} components and {len(edges)} connections."
        ]
        
        if len(nodes) == 0:
            summary_parts.append("No components detected in the diagram.")
            return "\n".join(summary_parts)
        
        # Count by type
        type_counts = {}
        for node_id, comp_type in component_types.items():
            type_counts[comp_type] = type_counts.get(comp_type, 0) + 1
        
        if type_counts:
            summary_parts.append("\nComponent breakdown by type:")
            for comp_type, count in sorted(type_counts.items()):
                summary_parts.append(f"  - {comp_type}: {count}")
        
        # List labeled components with their types
        labeled_components = []
        for node in nodes:
            node_id = node["id"]
            label = labels.get(node_id, "")
            comp_type = component_types.get(node_id, "unknown")
            if label:
                annot_str = ""
                if node_id in annotations:
                    annot_parts = []
                    for key, value in annotations[node_id].items():
                        annot_parts.append(f"{key}={value}")
                    annot_str = f" ({', '.join(annot_parts)})" if annot_parts else ""
                labeled_components.append(f"{label} [{comp_type}]{annot_str}")
        
        if labeled_components:
            summary_parts.append("\nLabeled components:")
            # Show all if <= 30, otherwise show first 30 + count
            if len(labeled_components) <= 30:
                for label in labeled_components:
                    summary_parts.append(f"  - {label}")
            else:
                for label in labeled_components[:30]:
                    summary_parts.append(f"  - {label}")
                summary_parts.append(f"  ... and {len(labeled_components) - 30} more labeled components")
        
        # Describe connections
        if edges:
            summary_parts.append(f"\nConnections ({len(edges)} total):")
            for edge in edges[:30]:  # Show first 30 connections
                from_label = labels.get(edge["from"], edge["from"][:8])
                to_label = labels.get(edge["to"], edge["to"][:8])
                conn_str = f"{from_label} → {to_label}"
                if edge.get("label"):
                    conn_str += f" [{edge['label']}]"
                summary_parts.append(f"  - {conn_str}")
            if len(edges) > 30:
                summary_parts.append(f"  ... and {len(edges) - 30} more connections")
        
        # Check for common architecture patterns
        pattern_checks = []
        if "load balancer" in str(labels).lower() or "lb" in str(labels).lower():
            pattern_checks.append("Load balancing detected")
        if "cache" in str(labels).lower() or "redis" in str(labels).lower():
            pattern_checks.append("Caching layer detected")
        if "queue" in str(labels).lower() or "kafka" in str(labels).lower():
            pattern_checks.append("Message queue detected")
        if any("replica" in str(ann).lower() for ann in annotations.values()):
            pattern_checks.append("Replication/redundancy detected")
        
        if pattern_checks:
            summary_parts.append("\nArchitecture patterns detected:")
            for pattern in pattern_checks:
                summary_parts.append(f"  - {pattern}")
        
        return "\n".join(summary_parts)

