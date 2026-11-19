//  c:/Users/saira/OneDrive/Desktop/Electoraw/frontend/app/components/IndiaMap.tsx
"use client";

import React from "react";

/** Simple placeholder map component.
 * Replace the SVG/path with your real map implementation later.
 */
const IndiaMap: React.FC = () => {
  return (
    <svg
      viewBox="0 0 1000 1200"
      width="100%"
      height="auto"
      aria-label="Map of India"
      role="img"
      style={{
        border: "1px solid #ccc",
        borderRadius: "8px",
        background: "linear-gradient(180deg, #e0f7fa, #e0f2f1)",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
      }}
    >
      {/* Very rough outline – replace with a proper SVG map of India */}
      <path
        d="M500,0 L600,100 L650,200 L620,300 L680,400 L640,500 L700,600 L660,700 L710,800 L610,900 L570,1000 L530,1100 L470,1100 L430,1000 L390,900 L340,800 L390,700 L350,600 L410,500 L370,400 L430,300 L400,200 L450,100 Z"
        fill="#90caf9"
        stroke="#1976d2"
        strokeWidth="5"
      />
      {/* Add any interactive parts (tooltips, click handlers) here */}
    </svg>
  );
};

export default IndiaMap;
