# ANNOTATION_GUIDE.md — CVAT & Label Studio YOLO Annotation Manual

**Platform:** Intelligent Border Video Analytics Platform (IBVAP)  
**Standard Classes:** 5 Classes (`person`, `car`, `motorcycle`, `truck`, `bus`)  
**Label Format:** Ultralytics YOLO (`<class_id> <x_center> <y_center> <width> <height>`)  

---

## 1. Class Taxonomy & Identification Rules

| Class ID | Class Name | What to Include | What to Exclude |
|:---:|---|---|---|
| `0` | `person` | Standing, walking, running, crouching humans, guards, infiltrators. Include backpacks/carried gear within bounding box. | Reflections in water/glass, mannequins, statues. |
| `1` | `car` | Civilian sedans, SUVs, hatchbacks, pickups, border patrol jeeps. | Heavy semi-trucks, buses, motorcycles. |
| `2` | `motorcycle` | Motorbikes, scooters, dirt bikes, quad bikes. If a rider is on the bike, label the bike as `motorcycle` and the rider separately as `person`. | Bicycles, unmounted helmets. |
| `3` | `truck` | Commercial lorries, flatbeds, cargo trucks, tankers, military troop transports. | Light civilian pickup trucks (label as `car`). |
| `4` | `bus` | Passenger coaches, minibuses, public transport buses. | Vans (label as `car` or `truck` depending on chassis). |

---

## 2. Bounding Box Boundary Protocol

1. **Tight Fit**: Boxes must bound the outermost visible pixels of the target without excessive background margin (< 5px padding).
2. **Ground Anchoring**: The bottom edge of the box must align with the target's physical ground-contact point.
3. **Partially Visible Objects**: If an object is cut off by the frame edge, enclose the visible portion only. Do **not** extrapolate unseen limbs/wheels.
4. **Occlusions**:
   - $\le 70\%$ occluded: Annotate visible target bounding box.
   - $> 70\%$ occluded: Do **NOT** annotate if features are indiscernible.
5. **Distant / Tiny Targets**:
   - Minimum pixel threshold: Objects smaller than 15x15 pixels must **NOT** be labeled (beyond optical recognition resolution).

---

## 3. Background Hard Negatives

- Uninhabited border terrain, fence posts, swaying shrubs, and animal wildlife must **NOT** be annotated.
- Leaving images with zero bounding boxes creates vital hard negatives that teach the detector to suppress false perimeter alarms.
