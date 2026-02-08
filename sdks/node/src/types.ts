export type ActionScan = {
  type: "scan";
  x: number;
  y: number;
  radius: number;
};

export type ActionSendFleet = {
  type: "send_fleet";
  from_id: number;
  to_id: number;
  energy: number;
};

export type ActionUpgrade = {
  type: "upgrade";
  planet_id: number;
  upgrade: "energy" | "silver" | "defense" | "speed" | "sensor";
};

export type Action = ActionScan | ActionSendFleet | ActionUpgrade;

export type PlanetView = {
  id: number;
  x: number;
  y: number;
  level: number;
  energy: number;
  energy_cap: number;
  silver: number;
  silver_cap: number;
  defense: number;
  speed: number;
  sensor_range: number;
  owner: number | null;
  is_artifact: boolean;
  visibility: string;
  last_seen_tick: number;
};

export type FleetView = {
  id: number;
  owner: number;
  source_id: number;
  dest_id: number;
  energy: number;
  ticks_remaining: number;
  total_ticks: number;
  x: number;
  y: number;
};

export type PingView = {
  id: number;
  x: number;
  y: number;
  radius: number;
  strength: number;
  source_player: number;
  tick: number;
};

export type Observation = {
  tick: number;
  player_id: number | null;
  planets: PlanetView[];
  fleets: FleetView[];
  pings: PingView[];
  scores: Array<{
    id: number;
    name: string;
    score: number;
    territory_score: number;
    artifact_score: number;
    artifacts_held: number;
  }>;
  max_actions: number;
};
