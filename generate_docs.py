from linkml_runtime import SchemaView
from pathlib import Path


def generate_filtered_docs(
    schema_path: str,
    output_dir: str = "docs",
    slots_only: bool = False
):
    """
    Generate documentation with filtered navigation.
    
    Args:
        schema_path: Path to your LinkML schema
        output_dir: Output directory for markdown files
        slots_only: If True, only generate slot pages (data dictionary style)
    """
    sv = SchemaView(schema_path)
    local_schema_id = sv.schema.id
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get local elements only
    local_slots = {
        name: slot for name, slot in sv.all_slots().items()
        if getattr(slot, 'from_schema', local_schema_id) == local_schema_id
    }
    
    local_classes = {
        name: cls for name, cls in sv.all_classes().items()
        if getattr(cls, 'from_schema', local_schema_id) == local_schema_id
    }
    
    local_enums = {
        name: enum for name, enum in sv.all_enums().items()
        if getattr(enum, 'from_schema', local_schema_id) == local_schema_id
    }
    
    print(f"Found {len(local_slots)} local slots")
    print(f"Found {len(local_classes)} local classes")
    print(f"Found {len(local_enums)} local enums")
    
    # Generate slot pages (data dictionary)
    slots_dir = output_path / "slots"
    slots_dir.mkdir(exist_ok=True)
    
    for slot_name, slot in local_slots.items():
        content = render_slot_page(sv, slot_name, slot)
        (slots_dir / f"{slot_name}.md").write_text(content)
    
    # Generate class pages
    if not slots_only and local_classes:
        classes_dir = output_path / "classes"
        classes_dir.mkdir(exist_ok=True)
        for cls_name, cls in local_classes.items():
            content = render_class_page(sv, cls_name, cls)
            (classes_dir / f"{cls_name}.md").write_text(content)
    
    # Generate enum pages
    if local_enums:
        enums_dir = output_path / "enums"
        enums_dir.mkdir(exist_ok=True)
        for enum_name, enum in local_enums.items():
            content = render_enum_page(sv, enum_name, enum)
            (enums_dir / f"{enum_name}.md").write_text(content)
    
    # Generate index
    index_content = render_index(sv, local_slots, local_classes, local_enums, slots_only)
    (output_path / "index.md").write_text(index_content)
    
    # Generate complete mkdocs.yml
    mkdocs_config = generate_mkdocs_config(
        sv.schema, local_slots, local_classes, local_enums, slots_only
    )
    (output_path.parent / "mkdocs.yml").write_text(mkdocs_config)
    print(f"\nGenerated mkdocs.yml with collapsible navigation")
    
    return local_slots, local_classes, local_enums


def case_insensitive_sort(names):
    """Sort names alphabetically, ignoring case."""
    return sorted(names, key=lambda x: x.lower())


def render_slot_page(sv: SchemaView, slot_name: str, slot) -> str:
    """Render a single slot page with full type information."""
    lines = [f"# {slot_name}", ""]
    
    if slot.description:
        lines.extend([slot.description, ""])
    
    # Comments
    if slot.comments:
        lines.extend(["## Comments", ""])
        for comment in slot.comments:
            lines.append(f"- {comment}")
        lines.append("")
    
    # Basic info table
    lines.extend([
        "## Details",
        "",
        "| Property | Value |",
        "|----------|-------|",
    ])
    
    # Range (type)
    range_val = slot.range or "string"
    range_display = range_val
    
    if range_val in sv.all_enums():
        range_display = f"[{range_val}](../enums/{range_val}.md)"
    elif range_val in sv.all_classes():
        range_display = f"[{range_val}](../classes/{range_val}.md)"
    elif range_val in sv.all_types():
        type_obj = sv.get_type(range_val)
        if type_obj and type_obj.uri:
            range_display = f"`{range_val}` ({type_obj.uri})"
        else:
            range_display = f"`{range_val}`"
    
    lines.append(f"| **Range** | {range_display} |")
    lines.append(f"| **Required** | {'Yes' if slot.required else 'No'} |")
    lines.append(f"| **Multivalued** | {'Yes' if slot.multivalued else 'No'} |")
    
    if slot.pattern:
        lines.append(f"| **Pattern** | `{slot.pattern}` |")
    
    if slot.minimum_value is not None:
        lines.append(f"| **Minimum** | {slot.minimum_value} |")
    
    if slot.maximum_value is not None:
        lines.append(f"| **Maximum** | {slot.maximum_value} |")
    
    if slot.unit:
        unit_info = slot.unit
        if hasattr(unit_info, 'symbol'):
            lines.append(f"| **Unit** | {unit_info.symbol} ({getattr(unit_info, 'ucum_code', '')}) |")
        else:
            lines.append(f"| **Unit** | {unit_info} |")
    
    if slot.in_subset:
        subsets = ", ".join(slot.in_subset)
        lines.append(f"| **Subsets** | {subsets} |")
    
    lines.append("")
    
    # Annotations
    if slot.annotations:
        lines.extend(["## Annotations", ""])
        lines.extend([
            "| Tag | Value |",
            "|-----|-------|",
        ])
        for ann_name, ann in slot.annotations.items():
            # Handle both simple values and annotation objects
            if hasattr(ann, 'value'):
                ann_value = ann.value
            else:
                ann_value = str(ann)
            lines.append(f"| `{ann_name}` | {ann_value} |")
        lines.append("")
    
    # Examples
    if slot.examples:
        lines.extend(["## Examples", ""])
        for ex in slot.examples:
            if hasattr(ex, 'value'):
                lines.append(f"- `{ex.value}`")
            else:
                lines.append(f"- `{ex}`")
        lines.append("")
    
    # Used in classes
    classes_using = [
        cls_name for cls_name, cls in sv.all_classes().items()
        if slot_name in sv.class_slots(cls_name)
    ]
    if classes_using:
        lines.extend(["## Used In", ""])
        for cls_name in case_insensitive_sort(classes_using):
            lines.append(f"- [{cls_name}](../classes/{cls_name}.md)")
        lines.append("")
    
    # Slot inheritance
    if slot.is_a:
        lines.extend([
            "## Inheritance",
            "",
            f"Inherits from: `{slot.is_a}`",
            ""
        ])
    
    # Mixins
    if slot.mixins:
        lines.extend(["## Mixins", ""])
        for mixin in slot.mixins:
            lines.append(f"- `{mixin}`")
        lines.append("")
    
    return "\n".join(lines)


def render_class_page(sv: SchemaView, cls_name: str, cls) -> str:
    """Render a class page."""
    lines = [f"# {cls_name}", ""]
    
    if cls.description:
        lines.extend([cls.description, ""])
    
    # Attributes table
    slots = sv.class_induced_slots(cls_name)
    if slots:
        lines.extend([
            "## Attributes",
            "",
            "| Name | Type | Description | Required |",
            "|------|------|-------------|----------|",
        ])
        # Sort slots alphabetically by name, case-insensitive
        sorted_slots = sorted(slots, key=lambda s: s.name.lower())
        for slot in sorted_slots:
            slot_link = f"[{slot.name}](../slots/{slot.name}.md)"
            range_val = slot.range or "string"
            desc = (slot.description or "").replace("\n", " ")[:100]
            req = "Yes" if slot.required else "No"
            lines.append(f"| {slot_link} | `{range_val}` | {desc} | {req} |")
        lines.append("")
    
    if cls.is_a:
        lines.extend([
            "## Inheritance",
            "",
            f"Inherits from: `{cls.is_a}`",
            ""
        ])
    
    return "\n".join(lines)


def render_enum_page(sv: SchemaView, enum_name: str, enum) -> str:
    """Render an enum page."""
    lines = [f"# {enum_name}", ""]
    
    if enum.description:
        lines.extend([enum.description, ""])
    
    lines.extend([
        "## Permitted Values",
        "",
        "| Value | Description |",
        "|-------|-------------|",
    ])
    
    if enum.permissible_values:
        # Sort permissible values alphabetically, case-insensitive
        sorted_pvs = case_insensitive_sort(enum.permissible_values.keys())
        for pv_name in sorted_pvs:
            pv = enum.permissible_values[pv_name]
            desc = ""
            if pv and hasattr(pv, 'description') and pv.description:
                desc = pv.description.replace("\n", " ")
            lines.append(f"| `{pv_name}` | {desc} |")
    
    lines.append("")
    return "\n".join(lines)


def render_index(sv, local_slots, local_classes, local_enums, slots_only) -> str:
    """Render the index page."""
    schema = sv.schema
    display_name = schema.title or schema.name or "Schema"
    lines = [
        f"# {display_name}",
        "",
    ]
    
    if schema.description:
        lines.extend([schema.description, ""])
    
    # Slots section (data dictionary)
    lines.extend([
        "## Data Dictionary",
        "",
        "| Field | Type | Description |",
        "|-------|------|-------------|",
    ])
    
    for slot_name in case_insensitive_sort(local_slots.keys()):
        slot = local_slots[slot_name]
        range_val = slot.range or "string"
        desc = (slot.description or "").replace("\n", " ")[:80]
        lines.append(f"| [{slot_name}](slots/{slot_name}.md) | `{range_val}` | {desc} |")
    
    lines.append("")
    
    if not slots_only and local_classes:
        lines.extend(["## Classes", ""])
        for cls_name in case_insensitive_sort(local_classes.keys()):
            lines.append(f"- [{cls_name}](classes/{cls_name}.md)")
        lines.append("")
    
    if local_enums:
        lines.extend(["## Enumerations", ""])
        for enum_name in case_insensitive_sort(local_enums.keys()):
            lines.append(f"- [{enum_name}](enums/{enum_name}.md)")
        lines.append("")
    
    return "\n".join(lines)

def create_custom_css(output_dir: str):
    """Create custom CSS to fix sidebar scrolling."""
    css_dir = Path(output_dir) / "css"
    css_dir.mkdir(exist_ok=True)
    
    css_content = """/* Fix the search bar at top, make only nav scroll */
.wy-side-scroll {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.wy-side-nav-search {
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 10;
}

.wy-menu-vertical {
  overflow-y: auto;
  flex-grow: 1;
}
"""
    (css_dir / "custom.css").write_text(css_content)

def generate_mkdocs_config(schema, local_slots, local_classes, local_enums, slots_only) -> str:
    """Generate a complete mkdocs.yml with collapsible, alphabetized navigation."""
    
    nav_lines = []
    nav_lines.append("  - Home: index.md")
    
    # Classes first
    if not slots_only and local_classes:
        nav_lines.append("  - Classes:")
        for cls_name in case_insensitive_sort(local_classes.keys()):
            nav_lines.append(f"      - {cls_name}: classes/{cls_name}.md")
    
    # Enums second
    if local_enums:
        nav_lines.append("  - Enumerations:")
        for enum_name in case_insensitive_sort(local_enums.keys()):
            nav_lines.append(f"      - {enum_name}: enums/{enum_name}.md")
    
    # Data Dictionary last
    nav_lines.append("  - Data Dictionary:")
    for slot_name in case_insensitive_sort(local_slots.keys()):
        nav_lines.append(f"      - {slot_name}: slots/{slot_name}.md")
    
    nav_yaml = "\n".join(nav_lines)
    schema_name = schema.title or schema.name or "Schema"
    
    config = f"""site_name: {schema_name}
site_description: Documentation for {schema_name}
docs_dir: docs

theme:
  name: readthedocs
  collapse_navigation: false
  sticky_navigation: true
  titles_only: false

plugins:
  - search

extra_css:
  - css/custom.css

markdown_extensions:
  - tables
  - admonition
  - toc:
      permalink: true

nav:
{nav_yaml}
"""
    return config
    

if __name__ == "__main__":
    import sys
    
    schema_path = sys.argv[1] if len(sys.argv) > 1 else "schema.yaml"
    generate_filtered_docs(schema_path, output_dir="docs", slots_only=False)