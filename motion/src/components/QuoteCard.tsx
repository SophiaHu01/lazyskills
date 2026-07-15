import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {QuoteCardProps} from '../types';
import {useEventTiming} from './timing';

// 引用卡:引用原话/金句定格,左侧 accent 竖线。

type Props = {
  event: {start: number; hold: number; props: QuoteCardProps};
};

export const QuoteCard: React.FC<Props> = ({event}) => {
  const {text, by} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  if (!visible) return null;
  const byFade = interpolate(local, [14, 26], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 380,
          background: tokens.paper,
          borderRadius: 28,
          padding: '44px 52px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderLeft: `12px solid ${tokens.accent}`,
          maxWidth: SAFE_WIDTH,
          boxSizing: 'border-box',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.92 + 0.08 * enter})`,
        }}
      >
        <div
          style={{
            fontFamily: tokens.font,
            fontWeight: 700,
            fontSize: 46,
            lineHeight: 1.5,
            color: tokens.ink,
          }}
        >
          {text}
        </div>
        {by ? (
          <div
            style={{
              fontFamily: tokens.font,
              fontWeight: 600,
              fontSize: 34,
              color: tokens.accent,
              textAlign: 'right',
              marginTop: 20,
              opacity: byFade,
            }}
          >
            {by}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
