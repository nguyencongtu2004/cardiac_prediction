// Types for helmet violation detection system

export interface Violation {
  violation_id: string;
  timestamp: string;
  camera_id: string;
  track_id: number;
  frame_number: number;
  confidence: number;
  bounding_box: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  image_base64?: string;
  image_path?: string;
  metadata: {
    person_detected: boolean;
    motorbike_detected: boolean;
    helmet_detected: boolean;
    num_helmets?: number;
  };
}

export interface Stats {
  total_violations: number;
  violations_today: number;
  violations_last_hour: number;
  by_camera: CameraCount[];
}

export interface CameraCount {
  camera_id: string;
  count: number;
}

export interface CameraFrame {
  camera_id: string;
  timestamp: string;
  frame_number: number;
  image_base64: string;
}
