# IFC Pipeline Testing and Validation Tools

This directory contains comprehensive testing tools for validating the 4-step IFC conversion pipeline:
**IFC → ifcJSON → simplified JSON → ifcJSON → IFC**

## 🎯 Testing Philosophy

Our testing approach measures **actual pipeline performance** against real IFC data and visual geometry, focusing on the most critical metrics that affect the final building model quality.

## 🛠️ Available Test Tools

### Core Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `compare_world_positions.py` | **PRIMARY** - Actual world coordinate accuracy | IFC files | Visual geometry positioning |
| `compare_ifcjson_elements.py` | **GEOMETRY** - Element geometry and representation comparison | ifcJSON files | Geometry structure differences |
| `extract_hierarchy_from_ifcjson.py` | Hierarchy from ifcJSON | Step 1/3 JSON | Placement structure |
| `extract_hierarchy_from_ifcjson_fixed.py` | Hierarchy from ifcJSON (ref format) | Step 3 JSON with refs | Fixed placement parsing |
| `extract_hierarchy_from_simplified.py` | Hierarchy from simplified | Step 2 JSON | Simplified placement |
| `compare_hierarchy.py` | Hierarchy preservation | Hierarchy JSON files | Cross-step comparison |
| `compare_placement_step2_step3.py` | Individual placement analysis | Step 2/3 JSON | Element-by-element debug |
| `analyze_missing_elements.py` | Element preservation | Pipeline outputs | Data loss analysis |

### IFC Structure Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `find_slabs.py` | **SLABS** - Find all IfcSlab entities in ifcJSON | ifcJSON files | Slab counts, types, and names |
| `find_containment.py` | **CONTAINMENT** - Find IfcRelContainedInSpatialStructure relationships | ifcJSON files | Element-to-storey relationships |
| `find_aggregation.py` | **AGGREGATION** - Find IfcRelAggregates relationships | ifcJSON files | Parent-child aggregation structures |
| `find_opening_elements.py` | **OPENINGS** - Find IfcOpeningElement entities and their relationships | IFC files | Opening counts, void/fill relationships, geometry representations |
| `compare_opening_elements.py` | **OPENING COMPARE** - Deep comparison of IfcOpeningElement between two IFC files | Two IFC files + opening name | Geometry details, placement differences, relationship analysis |

### Geometry Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `analyze_geometry_linkage.py` | **LINKAGE** - Element-to-geometry connection analysis | ifcJSON files | Geometry reference chains |
| `analyze_shape_representations.py` | **REPRESENTATIONS** - Shape representation structure analysis | ifcJSON files | Representation counts and types |
| `debug_embedded_converter.py` | **CONVERTER DEBUG** - ProductDefinitionShape analysis | ifcJSON files | Referenced vs unused representations |
| `analyze_geometry_context_issues.py` | **CONTEXT** - Geometry context handling through pipeline | Test directory | Context preservation analysis |
| `compare_wall_dimensions.py` | **WALL DIMENSIONS** - Compare wall geometry (dimensions, orientation, extrusion) | IFC/ifcJSON files + wall name | Placement, extrusion depth/direction, profile dimensions, opening counts |

### IfcFacetedBrep and Mesh Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `analyze_facetedbrep_faces.py` | **FACE ANALYSIS** - Analyze IfcFacetedBrep face counts in ifcJSON | Single ifcJSON file | Face/vertex counts, circular opening detection |
| `find_ifcfacetedbrep_assets.py` | **ASSET MESH** - Find and analyze IfcFacetedBrep entities in asset library | Asset directory | Face counts, vertex counts, complexity distribution |
| `compare_facetedbrep_counts.py` | **PIPELINE COMPARISON** - Compare IfcFacetedBrep between official and pipeline | Hardcoded paths | Face count distribution comparison |
| `analyze_wall_complexity.py` | **WALL GEOMETRY** - Analyze wall geometry complexity between pipeline steps | Step 1 + Step 3 ifcJSON + wall name | Face/vertex counts, geometry complexity changes |

### TODO #70 Body-Brep Debugging Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `debug_body_brep_loss.py` | **BREP LOSS** - Identify elements losing Body-Brep representations | Step 1 + Step 3 ifcJSON | Which elements lose Body-Brep, geometry complexity changes |
| `debug_opening_window_relationship.py` | **OPENING ANALYSIS** - Window/opening geometry relationship analysis | Step 1 + Step 3 ifcJSON | Void-fill relationships, geometry complexity comparison |
| `debug_asset_extraction.py` | **ASSET FLOW** - Trace geometry through asset extraction/recreation | Step 1 + Simplified + Step 3 + Assets | Asset preservation, where geometry conversion occurs |

### Opening Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `detect_circular_openings_from_ifcjson.py` | **⭐ CIRCULAR DETECTION** - Dual-method circular opening detection from IfcOpeningElement profile geometry | Single ifcJSON file | Parametric + tessellated detection, center/radius extraction, unit inference, comprehensive analysis |
| `analyze_opening_by_globalid.py` | **OPENING DETAIL** - Detailed opening geometry analysis by GlobalId | IFC file + GlobalId | Geometry type, face counts, circular pattern detection, Step 2 storage recommendations |
| `compare_opening_profiles.py` | **PROFILE COMPARISON** - Detailed profile geometry comparison between two IFC files | Two IFC files + GlobalId | Point-by-point analysis, circular vs rectangular detection, tessellation quality |
| `find_opening_by_name.py` | **FIND OPENING** - Find opening elements by name pattern | ifcJSON file + name pattern | Opening type, GlobalId, representation status |

#### ⭐ Featured Tool: Circular Opening Detection

**`detect_circular_openings_from_ifcjson.py`** - Advanced dual-method circular opening detection system

**Purpose:** Automatically detect circular openings directly from IfcOpeningElement profile geometry in ifcJSON files without requiring tessellation analysis or prior knowledge of element names.

**Usage:**
```bash
python detect_circular_openings_from_ifcjson.py /path/to/file.json
```

**Detection Methods:**
1. **Parametric Detection** - IfcIndexedPolyCurve with IfcArcIndex segments (4 control points)
2. **Tessellated Detection** - IfcPolyline with many points (≥8) using least squares circle fitting

**Key Features:**
- **Universal Compatibility**: Works with both parametric (4-point arcs) and tessellated (high-point polylines) representations
- **Unit Inference**: Automatically detects coordinate units (mm/m/units) and validates reasonable radii
- **High Accuracy**: Parametric detection achieves perfect precision (femtometer-level errors), tessellated achieves sub-percentage accuracy
- **Comprehensive Analysis**: Processes all IfcOpeningElement entities automatically
- **False Positive Filtering**: Distinguishes circular from rectangular/complex geometry using statistical validation
- **Multi-source Tested**: Successfully validated on OrangeHouse.ifc (tessellated), generated examples (parametric), and 014-hotel_arch.ifc (parametric)

**Output**: JSON report with detailed circular parameters (center, radius, quality metrics) and analysis metadata

**Test Results:**
- **OrangeHouse.json**: 2/17 openings detected as circular (500mm radius, tessellated method)
- **wall-circular examples**: 1/1 openings detected as circular (300mm radius, parametric method)  
- **014-hotel_arch.json**: 4/76 openings detected as circular (750mm radius, parametric method)

This tool addresses TODO #72-73 circular opening preservation challenges by providing early detection capabilities for pipeline integration.

### Debug Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `debug_step3_boolean_recreation.py` | **STEP 3 DEBUG** - Investigate boolean operations recreation in Step 3 | Simplified JSON + Assets + Wall name | Asset analysis, boolean operations tracing, Step 3 processing simulation |
| `trace_step3_boolean_processing.py` | **BOOLEAN TRACE** - Live tracing of Step 3 boolean operation processing | Simplified JSON + Assets + Output file | Real-time boolean operation processing, loss detection, entity counts |

### Advanced Representation Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `analyze_representation_types.py` | **REP TYPES** - Show specific representation types (Body-Brep, Body-SweptSolid) | Single ifcJSON + element name | Representation identifiers, geometry types, face counts |
| `extract_final_ifc_geometry.py` | **REAL GEOMETRY** - Extract actual face/vertex counts from final IFC using ifcopenshell | IFC file + element name | Real geometry as seen in viewers, face/vertex counts |
| `debug_representation_filtering.py` | **FILTER DEBUG** - Show which representations get filtered out and why | Step 1 + Step 3 ifcJSON | Which representations removed, complexity loss analysis |

### Wall Geometry Analysis Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `trace_wall_geometry_chain.py` | **⭐ GEOMETRY CHAIN** - Complete geometry entity tracing and comparison | Two ifcJSON files + wall name | Entity counts, circular polyline detection, boolean operations, geometry loss analysis |
| `analyze_wall_opening_geometry.py` | **OPENING ANALYSIS** - Analyze wall opening geometry differences in ifcJSON | Two ifcJSON files + wall name | Boolean operations, polyline shapes, circular vs rectangular detection |
| `compare_wall_geometry_details.py` | **GEOMETRY DETAILS** - Deep comparison of wall geometry entities | Two ifcJSON files + wall name | Polyline point counts, geometry entity distribution, simplification detection |

### Data Validation and Debug Tools

| Tool | Purpose | Input Format | Key Metrics |
|------|---------|--------------|-------------|
| `debug_entity_creation.py` | **ENTITY CREATION** - Debug which entity types fail ifcopenshell creation | Single ifcJSON file | Successful/failed entity creations |
| `debug_json2ifc_issue.py` | **JSON2IFC DEBUG** - Find problematic entities in JSON2IFC conversion | Single ifcJSON file | Entity validation issues |
| `debug_references.py` | **BROKEN REFS** - Find broken references in ifcJSON | Single ifcJSON file | Broken reference analysis |

### Utility Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `compare_official_roundtrip.py` | Local placement comparison | Debugging coordinate transforms |

## 📋 Complete Evaluation Guide

### Step 1: Run World Position Analysis (Primary Metric)

```bash
# Test specific output folder
python compare_world_positions.py ../../../out-b32292a --original ../../../ifc_files/OrangeHouse.ifc

# Test multiple folders
python compare_world_positions.py ../../../out-b32292a ../../../out-previous
```

**Expected Output:**
- Element preservation count (e.g., 37/80 elements)
- World position accuracy percentage (e.g., 94.6%)
- Visual quality assessment (EXCELLENT/GOOD/POOR/BROKEN)

### Step 2: Compare Element Geometry (When Elements are Invisible)

```bash
# Compare specific elements between official and pipeline ifcJSON
python compare_ifcjson_elements.py \
  ../../../out-official/json_outputs/OrangeHouse.json \
  ../../../out-wall/step3_expanded_json/OrangeHouse_expanded.json \
  EG-Fenster-6 EG-Fenster-7 Wand-Ext-ERDG-1

# Compare any elements between two ifcJSON files
python compare_ifcjson_elements.py file1.json file2.json ElementName1 ElementName2

# Deep dive using globalId or ref
python compare_ifcjson_elements.py file1.json file2.json f275e8f8-7416-420d-9b66-5fc8128d7ea5

# Mix names and IDs for investigation
python compare_ifcjson_elements.py file1.json file2.json EG-Fenster-6 window-prod-def-6d4a4bf-6c47-48b2-b561-71747079c39
```

**Expected Output:**
- Raw representation structure comparison
- Geometry analysis (embedded vs referenced, item count)
- Placement differences
- Reference analysis (what the element references and what references it)
- Opening/filling relationships for walls and slabs

**Enhanced Features:**
- Search by element name, globalId, or ref ID
- Shows reference chains to help trace hierarchy differences
- Identifies when IDs exist only as references but not as entities
- Useful for deep-diving into geometry structure differences

### Step 3: Extract Hierarchy from Each Pipeline Step

```bash
# Step 1: Original ifcJSON
python extract_hierarchy_from_ifcjson.py ../../../out-b32292a/step1_official_json/OrangeHouse.json step1_hierarchy.json

# Step 2: Simplified JSON
python extract_hierarchy_from_simplified.py ../../../out-b32292a/step2_simplified_json/OrangeHouse_simplified.json step2_hierarchy.json

# Step 3: Expanded ifcJSON (use fixed version for ref format)
python extract_hierarchy_from_ifcjson_fixed.py ../../../out-b32292a/step3_expanded_json/OrangeHouse_expanded.json step3_hierarchy.json
```

**Expected Output:**
- Total elements found in each step
- Elements with hierarchical placement
- Placement reference count
- Local coordinates for hierarchical elements

### Step 4: Compare Hierarchy Preservation

```bash
# Compare all three steps
python compare_hierarchy.py step1_hierarchy.json step2_hierarchy.json step3_hierarchy.json
```

**Expected Output:**
- Step 1→2 hierarchy preservation rate
- Step 2→3 hierarchy preservation rate  
- Overall pipeline hierarchy preservation
- Detailed element-by-element comparison

### Step 5: Analyze Missing Elements (Optional)

```bash
# Identify which elements are lost in the pipeline
python analyze_missing_elements.py ../../../out-b32292a
```

### Step 6: Debug Individual Placements (Optional)

```bash
# Compare specific element placements between Step 2 and Step 3
python compare_placement_step2_step3.py ../../../out-b32292a/step2_simplified_json/OrangeHouse_simplified.json ../../../out-b32292a/step3_expanded_json/OrangeHouse_expanded.json
```

### Step 6.5: Analyze IFC Structure (For Missing Elements/Relationships)

```bash
# Find all IfcSlab entities in an ifcJSON file
python find_slabs.py ../../../out-b32292a/step1_official_json/OrangeHouse.json

# Find containment relationships for specific elements
python find_containment.py ../../../out-b32292a/step1_official_json/OrangeHouse.json "element-id-1" "element-id-2"

# Find aggregation relationships for specific elements  
python find_aggregation.py ../../../out-b32292a/step1_official_json/OrangeHouse.json "parent-id" "child-id-1" "child-id-2"
```

**Expected Output:**
- Slab counts by predefined type (FLOOR, ROOF) with names and IDs
- Element-to-storey containment mapping
- Parent-child aggregation structures with relationship details

**When to Use:**
- **find_slabs.py**: When investigating missing slab elements or counting slab distribution
- **find_containment.py**: When elements appear in wrong storeys or have missing spatial relationships
- **find_aggregation.py**: When investigating missing aggregated roof/wall assemblies or complex element hierarchies

### Step 7: Analyze Geometry Structure (For Invisible Elements)

```bash
# Analyze element-to-geometry linkages
python analyze_geometry_linkage.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-b32292a/step3_expanded_json/OrangeHouse_expanded.json

# Analyze shape representations and contexts
python analyze_shape_representations.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-b32292a/step3_expanded_json/OrangeHouse_expanded.json ../../../out-b32292a/assets

# Debug embedded converter ProductDefinitionShape creation
python debug_embedded_converter.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-b32292a/step3_expanded_json/OrangeHouse_expanded.json
```

**Expected Output:**
- Element-to-geometry connection analysis
- Shape representation counts and types
- ProductDefinitionShape analysis (referenced vs unused)
- Geometry structure differences between official and pipeline output

### Step 8: Advanced IfcFacetedBrep Analysis (For Complex Geometry Issues)

```bash
# Analyze IfcFacetedBrep face counts in single ifcJSON file
python analyze_facetedbrep_faces.py ../../../out-todo70/step1_official_json/OrangeHouse.json

# Find IfcFacetedBrep entities in asset library and analyze complexity
python find_ifcfacetedbrep_assets.py ../../../out-todo70/assets/OrangeHouse/

# Compare IfcFacetedBrep counts between official and pipeline
python compare_facetedbrep_counts.py

# Analyze wall geometry complexity between steps
python analyze_wall_complexity.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# Analyze geometry context issues through pipeline
python analyze_geometry_context_issues.py ../../../out-todo70/
```

### Step 8.4: Opening Analysis (For TODO #72 Circular Opening Issues)

```bash
# Analyze specific opening by GlobalId for detailed geometry information
python analyze_opening_by_globalid.py ../../../ifc_files/OrangeHouse.ifc '0e2iWM3ICUNVYAkmP5YImx'

# Compare opening profiles between original and pipeline output
python compare_opening_profiles.py ../../../ifc_files/OrangeHouse.ifc ../../../out-temp/step4_final_ifc/OrangeHouse_roundtrip.ifc '0e2iWM3ICUNVYAkmP5YImx'

# Find all openings by name pattern
python find_opening_by_name.py ../../../out-temp/step1_official_json/OrangeHouse.json 'OG-Fenster'
```

**Expected Output (Opening Analysis):**
- **analyze_opening_by_globalid.py**: Geometry type detection, face/vertex counts, circular pattern analysis with center/radius calculations, Step 2 storage recommendations
- **compare_opening_profiles.py**: Point-by-point coordinate comparison, circular vs rectangular classification, tessellation quality assessment, geometry preservation analysis
- **find_opening_by_name.py**: Opening elements matching name pattern with type, GlobalId, and representation status

### Step 8.5: Debug Step 3 Processing (For Boolean Operation Loss)

```bash
# Debug Step 3 boolean recreation for specific wall
python debug_step3_boolean_recreation.py \
    ../../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \
    ../../../out-temp/assets/OrangeHouse \
    'Wand-Ext-OG-3'

# Live trace Step 3 boolean processing to see what happens in real-time
python trace_step3_boolean_processing.py \
    ../../../out-temp/step2_simplified_json/OrangeHouse_simplified.json \
    ../../../out-temp/assets/OrangeHouse \
    ./debug_step3_output.json
```

**Expected Output (Debug Tools):**
- **debug_step3_boolean_recreation.py**: Asset content analysis, boolean operations detection, Step 3 processing simulation, potential issue identification
- **trace_step3_boolean_processing.py**: Real-time asset loading traces, boolean operation preservation tracking, entity count summaries, loss detection

### Step 8.6: Advanced Representation Analysis (For TODO #70 Issues)

```bash
# Show specific representation types for an element (Body-Brep, Body-SweptSolid, etc.)
python analyze_representation_types.py ../../../out-official/json_outputs/OrangeHouse.json 'Wand-Ext-OG-1'
python analyze_representation_types.py ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# Extract REAL geometry from final IFC files (what viewers actually see)
python extract_final_ifc_geometry.py /Users/leixu/Downloads/bim/out-official/ifc_outputs/OrangeHouse_roundtrip.ifc 'Wand-Ext-OG-1'
python extract_final_ifc_geometry.py ../../../out-todo70/step4_final_ifc/OrangeHouse_roundtrip.ifc 'Wand-Ext-OG-1'

# Find elements with specific face counts (search mode)
python extract_final_ifc_geometry.py ../../../out-todo70/step4_final_ifc/OrangeHouse_roundtrip.ifc --search 135,130,37

# Debug which representations get filtered out during pipeline
python debug_representation_filtering.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# Analyze wall opening geometry differences in ifcJSON files
python analyze_wall_opening_geometry.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# Deep comparison of wall geometry entities
python compare_wall_geometry_details.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# ⭐ COMPLETE geometry chain tracing and comparison (MOST EFFECTIVE)
python trace_wall_geometry_chain.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'
```

**Expected Output (Advanced Geometry Analysis):**
- **analyze_facetedbrep_faces.py**: Face/vertex counts, circular opening candidates (125-140 faces)
- **find_ifcfacetedbrep_assets.py**: Asset library complexity distribution, target face counts (130, 135, 394)
- **compare_facetedbrep_counts.py**: Pipeline consistency validation for mesh geometry
- **analyze_wall_complexity.py**: Wall-specific geometry complexity comparison
- **analyze_geometry_context_issues.py**: Context preservation through 4-step pipeline

**Expected Output (Advanced Representation Analysis):**
- **analyze_representation_types.py**: Representation identifiers (Body-Brep, Body-SweptSolid), geometry types per representation, face counts for complex geometry
- **extract_final_ifc_geometry.py**: ⭐ **CRITICAL** - REAL face/vertex counts as seen in IFC viewers (e.g., 788→200 faces), complexity classification, actual geometry loss detection
- **debug_representation_filtering.py**: Which representations filtered out, why filtering occurred, geometry quality loss analysis

**Expected Output (Wall Geometry Analysis):**
- **trace_wall_geometry_chain.py**: ⭐ **MOST EFFECTIVE** - Complete entity tracing (253→2 entities), circular polyline detection, boolean operation analysis, comprehensive geometry loss identification
- **analyze_wall_opening_geometry.py**: Boolean operation traces, circular polyline detection, opening geometry classification, shape hints (circular vs rectangular)
- **compare_wall_geometry_details.py**: Polyline point count comparison, geometry entity distribution, high-resolution circular geometry loss detection

### Step 9: Debug Body-Brep Geometry Loss (TODO #70 Issues)

```bash
# Identify which elements lose Body-Brep representations
python debug_body_brep_loss.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json

# Focus on specific element with geometry loss
python debug_body_brep_loss.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'Wand-Ext-OG-1'

# Analyze window-opening relationship and geometry complexity
python debug_opening_window_relationship.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json 'OG-Fenster-2'

# Trace geometry through asset extraction and recreation
python debug_asset_extraction.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step2_simplified_json/OrangeHouse_simplified.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json ../../../out-todo70/assets/OrangeHouse 'Wand-Ext-OG-1'

# Analyze all Body-Brep elements (overview)
python debug_asset_extraction.py ../../../out-todo70/step1_official_json/OrangeHouse.json ../../../out-todo70/step2_simplified_json/OrangeHouse_simplified.json ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json ../../../out-todo70/assets/OrangeHouse
```

**Expected Output (TODO #70 Debugging):**
- **debug_body_brep_loss.py**: Which elements lose Body-Brep (21→10), geometry complexity changes (135→37 faces)
- **debug_opening_window_relationship.py**: Window/opening void-fill relationships, geometry type changes, complexity loss
- **debug_asset_extraction.py**: Asset flow tracing, where geometry conversion occurs (Step 2 vs Step 3)

### Step 10: Data Validation and Error Debugging

```bash
# Debug which entities fail ifcopenshell creation
python debug_entity_creation.py ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json

# Find problematic entities for JSON2IFC conversion
python debug_json2ifc_issue.py ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json

# Find broken references in ifcJSON
python debug_references.py ../../../out-todo70/step3_expanded_json/OrangeHouse_expanded.json
```

**Expected Output (Data Validation):**
- **debug_entity_creation.py**: Entity creation success/failure rates, problematic entity types
- **debug_json2ifc_issue.py**: Missing globalId/type fields, duplicate UUIDs, data structure issues
- **debug_references.py**: Broken reference chains, entities referenced but not defined

## 📊 Understanding Test Results

### Primary Metrics (Critical for Success)

1. **World Position Accuracy** - How accurately elements are positioned in 3D space
   - **100%**: Perfect positioning (visually identical)
   - **90-99%**: Minor differences (acceptable)
   - **70-89%**: Noticeable differences (may be acceptable)
   - **<70%**: Significant issues (problematic)

2. **Element Preservation** - How many building elements survive the pipeline
   - **80/80 (100%)**: All elements preserved (ideal)
   - **37/80 (46%)**: Major data loss (current typical result)
   - Focus on essential elements: walls, windows, doors, slabs, beams, columns

### Secondary Metrics (Important for Quality)

3. **Hierarchy Preservation** - Whether parent-child placement relationships are maintained
   - **Step 1→2**: Conversion from ifcJSON to simplified format
   - **Step 2→3**: Conversion from simplified back to ifcJSON
   - **100%**: Perfect hierarchy preservation
   - **0%**: Complete flattening of hierarchy

4. **Visual Quality Assessment** - Overall building model quality
   - **EXCELLENT**: No visible differences from original
   - **GOOD**: Minor visual differences, structurally sound
   - **POOR**: Noticeable issues but recognizable
   - **BROKEN**: Severe distortion, unusable

5. **Geometry Complexity Preservation** - How well complex geometry (IfcFacetedBrep) is preserved
   - **135+ faces**: High-resolution circular openings (ideal)
   - **130 faces**: Standard tessellation quality (acceptable)
   - **37 faces**: Simplified geometry (problematic for circular features)
   - **<20 faces**: Severely simplified geometry (poor quality)

## 🚨 Common Issues and Troubleshooting

### Issue: Elements are invisible in IFC viewer

**Cause**: Geometry representation differences between original and pipeline-processed ifcJSON.

**Debug Steps**:
1. Use `compare_ifcjson_elements.py` to compare geometry structures
2. Check if multiple representations are being reduced to single representations
3. Verify geometry types (IfcShapeRepresentation vs IfcMappedItem vs IfcExtrudedAreaSolid)
4. Check placement structure differences (embedded vs referenced)
5. Use `analyze_geometry_linkage.py` to trace element-to-geometry connections
6. Use `analyze_shape_representations.py` to analyze representation contexts and counts
7. Use `debug_embedded_converter.py` to check ProductDefinitionShape usage

### Issue: "Placement entity not found" in Step 3

**Cause**: Step 3 ifcJSON uses `{"ref": "id"}` format instead of embedded entities.

**Solution**: Use `extract_hierarchy_from_ifcjson_fixed.py` instead of the regular version for Step 3.

### Issue: Low hierarchy preservation in Step 2→3

**Root Cause**: `simplified_to_ifcjson.py` may not be correctly recreating hierarchical placement structures.

**Debug Steps**:
1. Run `compare_placement_step2_step3.py` to see individual element differences
2. Check if parent placement references are being lost
3. Verify local coordinate preservation

### Issue: Significant world position differences

**Root Cause**: Coordinate transformation errors in placement calculations.

**Debug Steps**:
1. Check specific elements with large position differences
2. Verify coordinate system transformations
3. Check if rotation matrices are being handled correctly

### Issue: Body-Brep geometry loss (TODO #70)

**Cause**: IfcFacetedBrep (circular mesh) converted to IfcExtrudedAreaSolid (rectangular) during pipeline

**Symptoms**:
- Circular openings appear rectangular in final IFC
- Significant geometry complexity loss (e.g., 135→37 faces, 394→100 vertices)
- Step 1 has 21 Body-Brep representations, Step 3 only has 10

**Debug Steps**:
1. Use `analyze_representation_types.py` to see which representation types exist (Body-Brep, Body-SweptSolid)
2. Use `extract_final_ifc_geometry.py` to get REAL face counts from final IFC files
3. Use `debug_representation_filtering.py` to see which representations get filtered out
4. Use `debug_body_brep_loss.py` to identify which elements lose Body-Brep
5. Use `debug_opening_window_relationship.py` to analyze specific window/opening geometry
6. Use `debug_asset_extraction.py` to trace where conversion occurs (Step 2 vs Step 3)
7. Use `analyze_facetedbrep_faces.py` to analyze face counts in ifcJSON files
8. Use `find_ifcfacetedbrep_assets.py` to analyze asset library complexity
9. Use `analyze_wall_complexity.py` to compare geometry between pipeline steps
10. Check if geometry types are missing from `GEOMETRY_ESSENTIAL_TYPES` in `ifc_constants.py`
11. Compare representation types: Body-Brep (complex) vs Body-SweptSolid (simple)

### Issue: JSON2IFC conversion failures

**Cause**: Malformed entity data, missing required fields, or broken references

**Debug Steps**:
1. Use `debug_json2ifc_issue.py` to validate entity structure
2. Use `debug_references.py` to find broken reference chains
3. Use `debug_entity_creation.py` to identify entities failing ifcopenshell creation

### Issue: Geometry context problems

**Cause**: IfcGeometricRepresentationContext entities not preserved correctly through pipeline

**Debug Steps**:
1. Use `analyze_geometry_context_issues.py` to trace context handling
2. Check if context deduplication is working correctly
3. Verify asset creation isn't creating empty or invalid contexts

## 🎯 Evaluation Benchmarks

### Excellent Performance (Target)
- World Position: **95%+**
- Element Preservation: **80/80**
- Hierarchy: **90%+** each step
- Visual Quality: **EXCELLENT**
- Geometry Complexity: **130+ faces** for circular features

### Acceptable Performance (Minimum)
- World Position: **85%+**
- Element Preservation: **70/80**
- Hierarchy: **70%+** each step
- Visual Quality: **GOOD**
- Geometry Complexity: **100+ faces** for circular features

### Current Performance (Latest)
- World Position: **95%+** ✅
- Element Preservation: **Variable** (depends on input complexity)
- Hierarchy: **100%** (Step 1→2), **100%** (Step 2→3) ✅
- Visual Quality: **EXCELLENT** ✅
- **Geometry Format**: **Fixed** - Now generates correct embedded_reference format ✅

## 📁 Required Directory Structure

For proper testing, ensure your output directory has this structure:

```
out-[commit]/
├── step1_official_json/
│   └── OrangeHouse.json
├── step2_simplified_json/
│   └── OrangeHouse_simplified.json
├── step3_expanded_json/
│   └── OrangeHouse_expanded.json
├── step4_final_ifc/
│   └── OrangeHouse_roundtrip.ifc
└── assets/
    └── OrangeHouse/
        ├── extracted_*.json
        └── ...
```

## 🔧 Tool Development Notes

### Core Tools
- **extract_hierarchy_from_ifcjson_fixed.py**: Enhanced version that handles ifcJSON `ref` format correctly
- **compare_placement_step2_step3.py**: Custom debugging tool for individual element analysis
- **compare_ifcjson_elements.py**: Advanced element comparison with geometry analysis

### Geometry Analysis Tools
- **analyze_geometry_linkage.py**: Traces element-to-geometry connections across two ifcJSON files
- **analyze_shape_representations.py**: Compares shape representation structures between official and pipeline output
- **debug_embedded_converter.py**: Analyzes ProductDefinitionShape usage and identifies unused representations
- **analyze_facetedbrep_faces.py**: Deep analysis of IfcFacetedBrep face/vertex counts
- **find_ifcfacetedbrep_assets.py**: Asset library mesh complexity analysis

### Advanced Debugging Tools
- **debug_body_brep_loss.py**: Specialized tool for tracing Body-Brep geometry loss
- **debug_asset_extraction.py**: Comprehensive asset flow tracing through pipeline
- **analyze_wall_complexity.py**: Wall-specific geometry complexity comparison
- **analyze_geometry_context_issues.py**: Geometry context preservation analysis
- **analyze_representation_types.py**: Detailed representation type analysis (Body-Brep, Body-SweptSolid)
- **extract_final_ifc_geometry.py**: Real geometry extraction from IFC files using ifcopenshell
- **debug_representation_filtering.py**: Representation filtering analysis and debugging

### Data Validation Tools
- **debug_entity_creation.py**: ifcopenshell entity creation validation
- **debug_json2ifc_issue.py**: JSON2IFC conversion issue detection
- **debug_references.py**: Broken reference chain analysis

### Compatibility
- All tools support both embedded entities and reference formats for maximum compatibility
- Tools automatically detect ifcJSON structure format and adapt accordingly
- Enhanced error handling for malformed or incomplete ifcJSON files

## 📈 Performance Tracking

Use these tools to track pipeline improvements over different commits:

```bash
# Quick evaluation of any output folder
python compare_world_positions.py ../../../out-[commit] --original ../../../ifc_files/OrangeHouse.ifc
python extract_hierarchy_from_ifcjson_fixed.py ../../../out-[commit]/step3_expanded_json/OrangeHouse_expanded.json hierarchy.json

# Geometry structure evaluation
python compare_ifcjson_elements.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-[commit]/step3_expanded_json/OrangeHouse_expanded.json "Element-Name"
python analyze_geometry_linkage.py ../../../out-official/json_outputs/OrangeHouse.json ../../../out-[commit]/step3_expanded_json/OrangeHouse_expanded.json

# Advanced geometry analysis
python analyze_facetedbrep_faces.py ../../../out-[commit]/step1_official_json/OrangeHouse.json
python find_ifcfacetedbrep_assets.py ../../../out-[commit]/assets/OrangeHouse/
```

## 🔍 Systematic Troubleshooting Workflow

When investigating pipeline issues, use this systematic approach:

### 1. Identify Problem Scope
```bash
python compare_world_positions.py ../../../out-[commit] --original ../../../ifc_files/OrangeHouse.ifc
```

### 2. Identify Problem Elements
```bash
python compare_ifcjson_elements.py official.json pipeline.json "Element-Name"
```

### 3. Analyze Geometry Structure
```bash
python analyze_geometry_linkage.py official.json pipeline.json
python analyze_shape_representations.py official.json pipeline.json assets/
```

### 4. Debug Specific Issues
```bash
# For invisible elements
python debug_embedded_converter.py official.json pipeline.json

# For complex geometry loss
python analyze_representation_types.py pipeline.json "Wall-Name"
python extract_final_ifc_geometry.py final.ifc "Wall-Name"
python debug_representation_filtering.py step1.json step3.json "Wall-Name"
python analyze_facetedbrep_faces.py pipeline.json
python find_ifcfacetedbrep_assets.py assets/
python analyze_wall_complexity.py step1.json step3.json "Wall-Name"

# For conversion errors
python debug_json2ifc_issue.py pipeline.json
python debug_references.py pipeline.json
```

### 5. Trace Pipeline Flow
```bash
python debug_asset_extraction.py step1.json simplified.json step3.json assets/ "Element-Name"
python debug_body_brep_loss.py step1.json step3.json "Element-Name"
```

The combination of world position accuracy, hierarchy preservation, correct geometry structure, and mesh complexity preservation provides a comprehensive assessment of pipeline quality and readiness for production use.

## 📚 Report Files

- **circular_opening_analysis_report.md**: Detailed analysis of 130-face vs 135-face IfcFacetedBrep investigation results
- Generated markdown reports from various analysis tools provide detailed findings for specific investigations

Total Tools: **37 Python analysis tools** + comprehensive documentation and workflows for complete IFC pipeline validation and debugging.

### 🔍 Most Effective Tool Combinations for Geometry Loss Investigation

**For TODO #72 Circular Opening Issues:**
1. **analyze_opening_by_globalid.py** - Detailed opening geometry analysis with recommendations
2. **compare_opening_profiles.py** - Point-by-point profile comparison (circular vs rectangular)
3. **trace_step3_boolean_processing.py** - Live boolean operation processing trace

**For TODO #71 Boolean Operation Loss:**
1. **debug_step3_boolean_recreation.py** - Step 3 asset processing investigation
2. **trace_step3_boolean_processing.py** - Real-time boolean operation tracking
3. **analyze_wall_complexity.py** - Wall geometry complexity changes

**For TODO #70 Circular Opening Issues:**
1. **trace_wall_geometry_chain.py** - Entity structure analysis (253→2 entities)
2. **extract_final_ifc_geometry.py** - Real face/vertex counts (788→200 faces) ⭐ **CRITICAL**
3. **analyze_representation_types.py** - Representation types (3→1 representations)

**Combined Usage:**
```bash
# Complete circular opening investigation workflow (TODO #72)
python analyze_opening_by_globalid.py original.ifc 'opening-globalid'
python compare_opening_profiles.py original.ifc pipeline.ifc 'opening-globalid'
python trace_step3_boolean_processing.py simplified.json assets/ debug_output.json

# Complete boolean operation investigation workflow (TODO #71)
python debug_step3_boolean_recreation.py simplified.json assets/ 'Wall-Name'
python trace_step3_boolean_processing.py simplified.json assets/ debug_output.json
python analyze_wall_complexity.py step1.json step3.json 'Wall-Name'

# Complete wall geometry investigation workflow (TODO #70)
python trace_wall_geometry_chain.py official.json pipeline.json 'Wall-Name'
python extract_final_ifc_geometry.py official.ifc 'Wall-Name'  
python extract_final_ifc_geometry.py pipeline.ifc 'Wall-Name'
python analyze_representation_types.py official.json 'Wall-Name'
python analyze_representation_types.py pipeline.json 'Wall-Name'
```

This combination reveals both **structural differences** (ifcJSON entity organization) and **actual geometry loss** (tessellation quality) that affects visual appearance.

### 📐 Wall Dimension Comparison Tool

**`compare_wall_dimensions.py`** - Comprehensive wall geometry comparison tool

**Purpose:** Compare wall dimensions, orientations, and extrusion information between two IFC or ifcJSON files. Essential for validating geometry preservation through the pipeline.

**Usage:**
```bash
python compare_wall_dimensions.py <file1> <file2> <wall_name>
```

**Examples:**
```bash
# Compare between original and roundtrip IFC files
python compare_wall_dimensions.py input/OrangeHouse.ifc out-temp2/step4_final_ifc/OrangeHouse_roundtrip.ifc "Wand-Ext-OG-1"

# Compare between step1 and step3 ifcJSON files
python compare_wall_dimensions.py out-temp2/step1_official_json/OrangeHouse.json out-temp2/step3_expanded_json/OrangeHouse_expanded.json "Wand-Ext-OG-3"

# Mixed format comparison
python compare_wall_dimensions.py original.ifc step3.json "Wall-Name"
```

**Key Features:**
- **Format Agnostic**: Works with both IFC and ifcJSON files
- **Placement Analysis**: Compares location, X/Y/Z axes, and transformation matrices
- **Geometry Analysis**: Extrusion depth, direction, and profile dimensions
- **Opening Detection**: Tracks associated openings and their counts
- **Tolerance Checking**: Uses configurable tolerance (default 1e-6) for numerical comparisons

**Output Details:**
1. **Placement Comparison**:
   - Location coordinates (X, Y, Z)
   - Axis directions (X-axis, Y-axis, Z-axis)
   - Difference measurements with pass/fail indicators

2. **Geometry Comparison**:
   - Extrusion depth
   - Extrusion direction vector
   - Profile type and dimensions (width, height for rectangles)
   - Arbitrary profile curve types

3. **Opening Analysis**:
   - Total opening count in each file
   - Openings only in file 1
   - Openings only in file 2
   - Common openings with GlobalId tracking

**Example Output:**
```
================================================================================
WALL COMPARISON: Wand-Ext-OG-1
================================================================================
File 1: input/OrangeHouse.ifc
File 2: out-temp2/step4_final_ifc/OrangeHouse_roundtrip.ifc

✅ Wall found in both files
   GlobalId 1: ec5748a-7cb6-4b3f-92fc-fb015a7d1d9
   GlobalId 2: ec5748a-7cb6-4b3f-92fc-fb015a7d1d9

📍 PLACEMENT COMPARISON
----------------------------------------
Location:
  File 1: [0.0, 0.0, 2.7]
  File 2: [0.0, 0.0, 2.7]
  Match: ✅ (diff: 0.000000)

X_AXIS:
  File 1: [0.0, 1.0, 0.0]
  File 2: [0.0, 1.0, 0.0]
  Match: ✅ (diff: 0.000000)

📐 GEOMETRY COMPARISON
----------------------------------------
Extrusion Depth:
  File 1: 0.49
  File 2: 0.49
  Match: ✅ (diff: 0.000000)

Extrusion Direction:
  File 1: [0.0, 0.0, 1.0]
  File 2: [0.0, 0.0, 1.0]
  Match: ✅ (diff: 0.000000)

🚪 OPENINGS COMPARISON
----------------------------------------
Opening Count:
  File 1: 2
  File 2: 2
  Match: ✅
```

This tool is particularly useful for:
- Validating geometry preservation through the 4-step pipeline
- Debugging placement/orientation issues
- Tracking opening element relationships
- Comparing original vs roundtrip IFC files
- Identifying dimensional changes or transformations