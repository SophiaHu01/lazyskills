import React from 'react';
import {AbsoluteFill, Easing, interpolate} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {BigNumberProps} from '../types';
import {useEventTiming} from './timing';

// 数字揭示:口播报出关键数字时,滚动计数进场的超大字。

type Props = {
  event: {start: number; hold: number; props: BigNumberProps};
};

const COUNT_F = 26; // 滚动计数时长(帧)

export const BigNumber: React.FC<Props> = ({event}) => {
  const {value, unit, label} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  if (!visible) return null;
  // 保留原数值的小数位数,滚动过程中位数不跳
  const decimals = (String(value).split('.')[1] ?? '').length;
  const progress = interpolate(local, [0, COUNT_F], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const shown = (value * progress).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  const labelFade = interpolate(local, [12, 24], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 400,
          background: tokens.paper,
          borderRadius: 28,
          padding: '56px 80px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderBottom: `8px solid ${tokens.accent}`,
          maxWidth: SAFE_WIDTH,
          textAlign: 'center',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.92 + 0.08 * enter})`,
        }}
      >
        <div style={{display: 'flex', alignItems: 'baseline', justifyContent: 'center', gap: 12}}>
          <span
            style={{
              fontFamily: tokens.font,
              fontWeight: 800,
              fontSize: 150,
              lineHeight: 1,
              color: tokens.accent,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {shown}
          </span>
          {unit ? (
            <span
              style={{
                fontFamily: tokens.font,
                fontWeight: 800,
                fontSize: 54,
                color: tokens.ink,
              }}
            >
              {unit}
            </span>
          ) : null}
        </div>
        {label ? (
          <div
            style={{
              fontFamily: tokens.font,
              fontWeight: 600,
              fontSize: 40,
              lineHeight: 1.4,
              color: tokens.ink,
              opacity: 0.78 * labelFade,
              marginTop: 18,
            }}
          >
            {label}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
