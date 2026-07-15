import React from 'react';
import {AbsoluteFill, interpolate} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {ChapterCardProps} from '../types';
import {useEventTiming} from './timing';

// 章节卡:内容换章时的大卡,居中偏上,编号 accent 色大字。

type Props = {
  event: {start: number; hold: number; props: ChapterCardProps};
};

function formatNo(no: number | string): string {
  return typeof no === 'number' ? String(no).padStart(2, '0') : no;
}

export const ChapterCard: React.FC<Props> = ({event}) => {
  const {no, title, sub} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  if (!visible) return null;
  const subFade = interpolate(local, [10, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 420, // 居中偏上
          background: tokens.paper,
          borderRadius: 28,
          padding: '52px 76px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderBottom: `8px solid ${tokens.accent}`,
          maxWidth: SAFE_WIDTH,
          textAlign: 'center',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.92 + 0.08 * enter})`,
        }}
      >
        <div
          style={{
            fontFamily: tokens.font,
            fontWeight: 800,
            fontSize: 112,
            lineHeight: 1,
            color: tokens.accent,
          }}
        >
          {formatNo(no)}
        </div>
        <div
          style={{
            fontFamily: tokens.font,
            fontWeight: 800,
            fontSize: 66,
            lineHeight: 1.25,
            color: tokens.ink,
            marginTop: 20,
          }}
        >
          {title}
        </div>
        {sub ? (
          <div
            style={{
              fontFamily: tokens.font,
              fontWeight: 600,
              fontSize: 40,
              lineHeight: 1.4,
              color: tokens.ink,
              opacity: 0.72 * subFade,
              marginTop: 14,
            }}
          >
            {sub}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
