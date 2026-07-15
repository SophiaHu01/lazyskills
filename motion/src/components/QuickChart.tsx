import React from 'react';
import {AbsoluteFill, spring, useVideoConfig} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {QuickChartProps} from '../types';
import {useEventTiming} from './timing';

// 快速图表:两个以上数字要对比时的竖屏友好横向条形图。
// 条从 0 弹性长出,highlight 项用 highlight 色,数值标在条端。纯 div 画,不接图表库。

type Props = {
  event: {start: number; hold: number; props: QuickChartProps};
};

const BAR_H = 46;
const STAGGER_F = 5; // 每条错开的帧数

export const QuickChart: React.FC<Props> = ({event}) => {
  const {items, unit} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  const {fps} = useVideoConfig();
  if (!visible || items.length === 0) return null;
  const maxValue = Math.max(...items.map((it) => it.value), 1e-9);
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 380,
          background: tokens.paper,
          borderRadius: 28,
          padding: '44px 48px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderBottom: `8px solid ${tokens.accent}`,
          width: SAFE_WIDTH,
          boxSizing: 'border-box',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.94 + 0.06 * enter})`,
        }}
      >
        {items.map((it, i) => {
          const grow = spring({
            frame: Math.max(0, local - 6 - i * STAGGER_F),
            fps,
            config: {damping: 15, stiffness: 110},
            durationInFrames: 26,
          });
          const frac = (it.value / maxValue) * grow;
          const barColor = it.highlight ? tokens.highlight : tokens.accent;
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                marginTop: i === 0 ? 0 : 22,
              }}
            >
              <div
                style={{
                  fontFamily: tokens.font,
                  fontWeight: it.highlight ? 800 : 600,
                  fontSize: 34,
                  color: tokens.ink,
                  width: 190,
                  textAlign: 'right',
                  marginRight: 20,
                  flexShrink: 0,
                }}
              >
                {it.label}
              </div>
              <div style={{flex: 1, display: 'flex', alignItems: 'center', minWidth: 0}}>
                <div
                  style={{
                    width: `${Math.max(frac, 0) * 76}%`,
                    minWidth: 6,
                    height: BAR_H,
                    borderRadius: 12,
                    background: barColor,
                    boxShadow: '0 2px 6px rgba(38,32,25,0.22)',
                  }}
                />
                <span
                  style={{
                    fontFamily: tokens.font,
                    fontWeight: 800,
                    fontSize: 34,
                    color: tokens.ink,
                    marginLeft: 14,
                    whiteSpace: 'nowrap',
                    opacity: grow,
                    fontVariantNumeric: 'tabular-nums',
                  }}
                >
                  {it.value.toLocaleString('en-US')}
                  {unit ?? ''}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
