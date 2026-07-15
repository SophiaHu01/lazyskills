import React from 'react';
import {AbsoluteFill, interpolate, spring, useVideoConfig} from 'remotion';
import {tokens} from '../tokens';
import type {CalloutProps} from '../types';
import {useEventTiming} from './timing';

// 指点强调:「看这里」——指向画面某区域。归一化坐标(0-1)定位。
// arrow=SVG path 弹性箭头;circle=描边圆圈脉冲两下;underline=左→右划出的高亮线。

type Props = {
  event: {start: number; hold: number; props: CalloutProps};
};

const CANVAS_W = 1080;
const CANVAS_H = 1920;

export const Callout: React.FC<Props> = ({event}) => {
  const {shape, x, y, w, h, label} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  const {fps} = useVideoConfig();
  if (!visible) return null;

  const px = x * CANVAS_W;
  const py = y * CANVAS_H;
  const pw = (w ?? 0.22) * CANVAS_W;
  const ph = (h ?? 0.07) * CANVAS_H;

  // 圆圈脉冲两下(进场稳定后,两个正弦鼓包)
  const pulse =
    shape === 'circle'
      ? interpolate(local, [20, 28, 36, 44, 52], [0, 0.06, 0, 0.06, 0], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        })
      : 0;

  // 箭头:尾部朝画面内侧,指向目标点
  const dirX = x < 0.5 ? 1 : -1;
  const dirY = y < 0.5 ? 1 : -1;
  const tailX = px + dirX * 170;
  const tailY = py + dirY * 230;
  const midX = (px + tailX) / 2 + dirY * 46;
  const midY = (py + tailY) / 2;
  // 箭头头部方向(控制点→目标点)
  const hdx = px - midX;
  const hdy = py - midY;
  const hlen = Math.hypot(hdx, hdy) || 1;
  const ux = hdx / hlen;
  const uy = hdy / hlen;
  const headBaseX = px - ux * 52;
  const headBaseY = py - uy * 52;
  const perpX = -uy;
  const perpY = ux;
  // 箭杆止于箭头底部,不穿过三角
  const shaftEndX = px - ux * 40;
  const shaftEndY = py - uy * 40;
  // 进场:沿来向滑入
  const slide = (1 - enter) * 70;

  const labelPop = spring({
    frame: Math.max(0, local - 8),
    fps,
    config: {damping: 14, stiffness: 160},
    durationInFrames: 16,
  });
  // label 位置:arrow 挂在尾部,circle/underline 挂在标记下方
  const labelX = shape === 'arrow' ? tailX : px;
  const labelY = shape === 'arrow' ? tailY + dirY * 26 : py + ph / 2 + 30;

  return (
    <AbsoluteFill>
      {shape === 'arrow' ? (
        <svg
          width={CANVAS_W}
          height={CANVAS_H}
          viewBox={`0 0 ${CANVAS_W} ${CANVAS_H}`}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            opacity,
            transform: `translate(${dirX * slide}px, ${dirY * slide}px)`,
          }}
        >
          <path
            d={`M ${tailX} ${tailY} Q ${midX} ${midY} ${shaftEndX} ${shaftEndY}`}
            stroke={tokens.accent}
            strokeWidth={16}
            strokeLinecap="round"
            fill="none"
          />
          <polygon
            points={`${px},${py} ${headBaseX + perpX * 30},${headBaseY + perpY * 30} ${headBaseX - perpX * 30},${headBaseY - perpY * 30}`}
            fill={tokens.accent}
          />
        </svg>
      ) : null}

      {shape === 'circle' ? (
        <div
          style={{
            position: 'absolute',
            left: px - pw / 2,
            top: py - ph / 2,
            width: pw,
            height: ph,
            borderRadius: '50%',
            border: `10px solid ${tokens.accent}`,
            boxSizing: 'border-box',
            opacity,
            transform: `scale(${(0.55 + 0.45 * enter) * (1 + pulse)})`,
          }}
        />
      ) : null}

      {shape === 'underline' ? (
        <div
          style={{
            position: 'absolute',
            left: px - pw / 2,
            top: py,
            width: pw,
            height: Math.max(10, Math.min(ph, 26)),
            borderRadius: 8,
            background: tokens.highlight,
            opacity: 0.92 * opacity,
            transform: `scaleX(${enter}) rotate(-1deg)`,
            transformOrigin: 'left center',
          }}
        />
      ) : null}

      {label ? (
        <div
          style={{
            position: 'absolute',
            left: labelX,
            top: labelY,
            transform: `translateX(-50%) scale(${0.8 + 0.2 * labelPop})`,
            background: tokens.paper,
            borderRadius: 14,
            padding: '12px 26px',
            boxShadow: '0 8px 24px rgba(38,32,25,0.3)',
            borderBottom: `5px solid ${tokens.accent}`,
            fontFamily: tokens.font,
            fontWeight: 800,
            fontSize: 36,
            color: tokens.ink,
            whiteSpace: 'nowrap',
            opacity: Math.min(labelPop, opacity),
          }}
        >
          {label}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
