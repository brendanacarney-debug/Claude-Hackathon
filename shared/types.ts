// Shared TypeScript types matching the backend JSON contract exactly.
// Keep in sync with backend/models.py.

export type ObjectCategory =
  | 'bed' | 'nightstand' | 'chair' | 'table' | 'door'
  | 'toilet' | 'shelf' | 'cord' | 'clutter' | 'lamp'
  | 'grab_bar' | 'walker' | 'shower' | 'bathtub'
  | 'counter' | 'cabinet' | 'rug' | 'other';

export type HazardClass =
  | 'floor_obstacle'
  | 'path_obstruction'
  | 'transfer_challenge'
  | 'bathroom_risk'
  | 'reachability_issue'
  | 'lighting_issue'
  | 'wound_care_issue';

export type Severity = 'urgent' | 'moderate' | 'low';

export type RecommendationCategory = 'remove' | 'move' | 'add' | 'adjust' | 'professional';

export type SessionStatus = 'created' | 'uploading' | 'analyzing' | 'analyzed' | 'error';

export type RoomType = 'bedroom' | 'bathroom' | 'hallway';

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Dimensions {
  width: number;
  height: number;
  depth: number;
}

export interface RoomObject {
  object_id: string;
  category: ObjectCategory;
  description?: string;
  position: Vector3;
  dimensions: Dimensions;
  on_primary_path: boolean;
  floor_level?: boolean;
  confidence: number;
}

export interface Room {
  room_id: string;
  room_type: RoomType;
  objects: RoomObject[];
  dimensions?: { width: number; length: number };
  floor_type?: string;
  lighting_quality?: string;
  overall_clutter_level?: string;
}

export interface Hazard {
  hazard_id: string;
  // 'class' is valid as a TypeScript property name (reserved only as a statement keyword)
  class: HazardClass;
  severity: Severity;
  explanation: string;
  related_object_ids: string[];
  recommendation_ids: string[];
}

export interface Recommendation {
  recommendation_id: string;
  priority: number;
  category: RecommendationCategory;
  text: string;
  target_location: string;
  expected_benefit: string;
}

export interface Waypoint extends Vector3 {
  label: string;
}

export interface SafePath {
  waypoints: Waypoint[];
  width_ok: boolean;
  min_width_m: number;
}

export interface GhostRearrangement {
  object_id: string;
  action: 'remove' | 'move';
  new_position: Vector3;
  reason: string;
}

export interface Checklist {
  first_night: string[];
  first_48_hours: string[];
}

export interface Session {
  session_id: string;
  created_at: string;
  recovery_profile: string;
  status: SessionStatus;
  rooms: Room[];
  hazards: Hazard[];
  recommendations: Recommendation[];
  safe_path: SafePath;
  checklist: Checklist;
  ghost_rearrangements: GhostRearrangement[];
  images: { originals: string[]; annotated: string[] };
  disclaimer: string;
  error_message?: string;
}

export interface RecoveryProfile {
  profile_id: string;
  label: string;
  constraints: string[];
  min_path_width_m: number;
  hazard_weights: Record<HazardClass, number>;
}
