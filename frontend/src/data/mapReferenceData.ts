export interface StateLabel {
  id: string;
  name: string;
  x: number;
  y: number;
  color?: string;
  fontSize?: number;
}

// State text labels matching user reference image media_1789034518976.png
export const STATE_LABELS: StateLabel[] = [
  { id: "jk", name: "Jammu & Kashmir", x: 215, y: 155, fontSize: 8 },
  { id: "ladakh", name: "Ladakh", x: 280, y: 155, fontSize: 8 },
  { id: "hp", name: "Himachal Pradesh", x: 245, y: 210, fontSize: 7.5 },
  { id: "pb", name: "Punjab", x: 200, y: 242, fontSize: 7.5 },
  { id: "ut", name: "Uttarakhand", x: 275, y: 255, fontSize: 7.5 },
  { id: "hr", name: "Haryana", x: 215, y: 270, fontSize: 7.5 },
  { id: "dl", name: "Delhi", x: 228, y: 285, fontSize: 6.5 },
  { id: "rj", name: "Rajasthan", x: 175, y: 315, fontSize: 9 },
  { id: "up", name: "Uttar Pradesh", x: 295, y: 305, fontSize: 9 },
  { id: "br", name: "Bihar", x: 370, y: 315, fontSize: 8.5 },
  { id: "sk", name: "Sikkim", x: 396, y: 268, fontSize: 7 },
  { id: "ar", name: "Arunachal Pradesh", x: 475, y: 260, fontSize: 7.5 },
  { id: "as", name: "Assam", x: 440, y: 308, fontSize: 8 },
  { id: "nl", name: "Nagaland", x: 495, y: 305, fontSize: 7.5 },
  { id: "mn", name: "Manipur", x: 485, y: 335, fontSize: 7.5 },
  { id: "mz", name: "Mizoram", x: 470, y: 375, fontSize: 7.5 },
  { id: "tr", name: "Tripura", x: 432, y: 360, fontSize: 7 },
  { id: "ml", name: "Meghalaya", x: 418, y: 325, fontSize: 7 },
  { id: "wb", name: "West Bengal", x: 395, y: 360, fontSize: 8 },
  { id: "jh", name: "Jharkhand", x: 355, y: 355, fontSize: 8 },
  { id: "or", name: "Odisha", x: 345, y: 430, fontSize: 8.5 },
  { id: "ct", name: "Chhattisgarh", x: 310, y: 410, fontSize: 8 },
  { id: "mp", name: "Madhya Pradesh", x: 245, y: 375, fontSize: 9 },
  { id: "gj", name: "Gujarat", x: 125, y: 395, fontSize: 9 },
  { id: "mh", name: "Maharashtra", x: 215, y: 470, fontSize: 9 },
  { id: "tg", name: "Telangana", x: 275, y: 470, fontSize: 8.5 },
  { id: "ap", name: "Andhra Pradesh", x: 280, y: 535, fontSize: 8.5 },
  { id: "ka", name: "Karnataka", x: 205, y: 565, fontSize: 8.5 },
  { id: "ga", name: "Goa", x: 175, y: 530, fontSize: 6.5 },
  { id: "kl", name: "Kerala", x: 200, y: 648, fontSize: 8 },
  { id: "tn", name: "Tamil Nadu", x: 255, y: 640, fontSize: 8.5 }
];

// Exact island coordinates matching user reference image
export const ANDAMAN_REFERENCE_PATHS = [
  // North & Middle Andaman
  "M 503 440 C 506 434, 510 436, 511 443 L 512 480 C 512 486, 508 488, 505 484 L 502 446 Z",
  // South Andaman
  "M 504 492 C 507 488, 511 489, 512 496 L 512 524 C 511 530, 507 531, 504 527 L 502 497 Z",
  // Little Andaman
  "M 500 540 C 504 537, 508 539, 508 545 L 507 554 C 506 558, 501 559, 499 555 L 499 543 Z",
  // Car Nicobar
  "M 508 572 C 512 569, 516 572, 515 577 C 514 582, 509 583, 506 580 C 504 577, 505 573, 508 572 Z",
  // Central Nicobar
  "M 514 590 C 518 587, 521 590, 520 596 C 519 600, 514 602, 512 598 C 510 595, 512 591, 514 590 Z",
  // Great Nicobar
  "M 518 608 C 523 605, 528 608, 527 616 L 526 624 C 524 628, 518 629, 515 625 L 516 612 Z"
];

export const LAKSHADWEEP_REFERENCE_PATHS = [
  // Chetlat & Kiltan (North)
  "M 96 585 C 99 582, 103 584, 102 589 C 101 593, 97 594, 95 590 Z",
  "M 104 592 C 107 589, 110 591, 110 596 C 109 599, 105 600, 103 597 Z",
  // Kadmat & Amini
  "M 98 604 C 101 601, 105 602, 104 608 L 103 615 C 102 618, 97 618, 97 614 Z",
  // Agatti
  "M 86 615 C 89 612, 93 614, 92 619 L 91 627 C 90 630, 85 630, 85 626 Z",
  // Kavaratti & Andrott
  "M 94 632 C 98 629, 102 631, 101 637 C 100 641, 95 642, 92 638 Z",
  "M 108 630 C 112 627, 116 629, 115 635 C 114 639, 109 640, 107 637 Z",
  // Kalpeni
  "M 105 646 C 108 643, 112 645, 111 651 C 110 655, 105 656, 103 653 Z",
  // Minicoy (South)
  "M 98 672 C 102 668, 108 671, 107 678 C 106 684, 99 685, 96 681 Z"
];
