// Scene four's geometry, in a 1600x900 reference frame. Each card's sprite is
// drawn by tools/build_project_cards.py from public/data/projects.json into the
// box and screen outline recorded here and in tools/data/card_quads.json;
// this module records where each piece goes.
//
// Coordinates are reference-frame pixels. fitCover() maps the frame onto the
// viewport the way the plate shader does (cover: fill, centre-anchored), so
// the DOM cards and the canvas can never drift apart.

export const FRAME = [1600, 900];

export const CARDS = [
  { id: 'p01_smartpix', title: 'SmartPix',
    box: [213, 72, 384, 273], depth: 0.45,
    tint: [0.309, 0.334, 0.382] },
  { id: 'p02_structai', title: 'StructAI',
    box: [63, 251, 428, 269], depth: 0.25,
    tint: [0.249, 0.267, 0.295] },
  { id: 'p03_hotelpulse', title: 'HotelPulse AI',
    box: [566, 41, 471, 288], depth: 0.6,
    tint: [0.414, 0.291, 0.291] },
  { id: 'p04_printflow', title: 'PrintFlow AI',
    box: [998, 95, 460, 377], depth: 0.45,
    tint: [0.322, 0.278, 0.261] },
  { id: 'p05_faceattend', title: 'Smart Face Recognition Attendance',
    box: [394, 358, 232, 198], depth: 0.8,
    tint: [0.39, 0.303, 0.234] },
  { id: 'p06_planttalk', title: 'PlantTalk AI',
    box: [568, 364, 173, 203], depth: 0.9,
    tint: [0.336, 0.324, 0.333] },
  { id: 'p07_restaurant', title: 'Smart Restaurant',
    box: [698, 366, 211, 204], depth: 1.0,
    tint: [0.336, 0.243, 0.217] },
  { id: 'p08_attendiq', title: 'Attendance Automation',
    box: [844, 370, 195, 206], depth: 0.9,
    tint: [0.26, 0.32, 0.366] },
  { id: 'p09_recommender', title: 'Product Recommendation System',
    box: [988, 364, 231, 208], depth: 0.8,
    tint: [0.336, 0.283, 0.269] },
  { id: 'p10_dashboards', title: 'Analytics Dashboards',
    box: [1181, 251, 355, 242], depth: 0.3,
    tint: [0.448, 0.305, 0.235] },
  { id: 'p11_certs', title: 'Certifications',
    box: [118, 467, 345, 243], depth: 0.1,
    tint: [0.311, 0.339, 0.263] },
  { id: 'p12_awards', title: 'Achievements',
    box: [1139, 478, 325, 234], depth: 0.1,
    tint: [0.31, 0.317, 0.302] },
];

// the central figure: crop box in frame px (his lighting is baked in)
export const PERSON = { x: 718, y: 483, w: 160, h: 335 };

// the floor's lit ellipses (centre x, centre y, rx, ry) and the overhead ring,
// used by the live glints the canvas draws over the baked plate
export const FLOOR_OUT = [798, 735, 372, 80];
export const FLOOR_IN = [798, 741, 240, 57];
export const RING = [802, 34, 392, 148];

/** Cover-fit the reference frame onto a viewport. */
export function fitCover(w, h) {
  const s = Math.max(w / FRAME[0], h / FRAME[1]);
  return { s, ox: (w - FRAME[0] * s) / 2, oy: (h - FRAME[1] * s) / 2 };
}

// --------------------------------------------------------------------------
// Portrait is a recomposition, not a crop: cover-fitting a 16:9 amphitheatre
// to a phone leaves only the centre quarter on screen. The plate still cover-
// fits (floor, circle and haze survive centred), and a curated set of cards
// restacks into a column that keeps the reference hierarchy: hero screen up
// top, the small row over the figure, the two green closers at his feet.
// Entries: card index -> centre x/y (viewport fractions), width (vw fraction).
// --------------------------------------------------------------------------
export const PORTRAIT = new Map([
  [2, { cx: 0.50, cy: 0.235, w: 0.80 }],   // build
  [0, { cx: 0.235, cy: 0.385, w: 0.50 }],  // timeless
  [3, { cx: 0.77, cy: 0.39, w: 0.48 }],    // driven
  [6, { cx: 0.325, cy: 0.53, w: 0.29 }],   // food
  [7, { cx: 0.675, cy: 0.53, w: 0.29 }],   // travel
  [10, { cx: 0.20, cy: 0.815, w: 0.48 }],  // cleaner
  [11, { cx: 0.80, cy: 0.815, w: 0.48 }],  // steps
]);
