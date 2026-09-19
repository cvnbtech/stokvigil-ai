import React from "react";

export function IciciDirectLogo({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0, borderRadius: size * 0.28, overflow: "hidden" }}
    >
      <defs>
        <linearGradient id="icici_grad" x1="0" y1="0" x2="24" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#A32338" />
          <stop offset="100%" stopColor="#F37021" />
        </linearGradient>
      </defs>
      <rect width="24" height="24" rx="6" fill="url(#icici_grad)" />
      {/* ICICI 'i' stylized emblem */}
      <circle cx="12" cy="7.2" r="2.2" fill="#FFFFFF" />
      <path d="M10 11.2H13.2V17H14.5V18.8H9.5V17H10.8V13.2H10V11.2Z" fill="#FFFFFF" />
    </svg>
  );
}

export function ZerodhaLogo({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0, borderRadius: size * 0.28, overflow: "hidden" }}
    >
      <rect width="24" height="24" rx="6" fill="#181F30" />
      {/* Zerodha Origami Kite Facets */}
      <polygon points="12,3.8 19,10.5 12,12.5" fill="#387ED1" />
      <polygon points="12,12.5 19,10.5 12,20.2" fill="#1C5393" />
      <polygon points="12,3.8 12,12.5 5,10.5" fill="#EA532A" />
      <polygon points="12,12.5 12,20.2 5,10.5" fill="#C4340F" />
    </svg>
  );
}

export function AngelOneLogo({ size = 18 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0, borderRadius: size * 0.28, overflow: "hidden" }}
    >
      <defs>
        <linearGradient id="angel_grad" x1="4" y1="4" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF3E30" />
          <stop offset="100%" stopColor="#FF851B" />
        </linearGradient>
      </defs>
      <rect width="24" height="24" rx="6" fill="#111728" />
      {/* Angel One Wing Chevron A */}
      <path d="M5.8 17.2L12 5.2L18.2 17.2H14.8L12 11.5L9.2 17.2H5.8Z" fill="url(#angel_grad)" />
      <circle cx="12" cy="15.2" r="2" fill="#FF851B" />
    </svg>
  );
}
