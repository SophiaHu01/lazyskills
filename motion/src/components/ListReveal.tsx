import React from 'react';
import {AbsoluteFill, spring, useVideoConfig} from 'remotion';
import {SAFE_WIDTH, tokens} from '../tokens';
import type {ListRevealProps} from '../types';
import {useEventTiming} from './timing';

// 列表逐条:并列要点逐条弹出(VidCaption CardLayer 的升级版,每条间隔 10 帧)。

type Props = {
  event: {start: number; hold: number; props: ListRevealProps};
};

const ITEM_STAGGER_F = 10;

export const ListReveal: React.FC<Props> = ({event}) => {
  const {title, items} = event.props;
  const {local, visible, enter, opacity} = useEventTiming(event.start, event.hold);
  const {fps} = useVideoConfig();
  if (!visible) return null;
  return (
    <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
      <div
        style={{
          marginBottom: 380,
          background: tokens.paper,
          borderRadius: 28,
          padding: '40px 56px',
          boxShadow: '0 14px 44px rgba(38,32,25,0.35)',
          borderBottom: `8px solid ${tokens.accent}`,
          maxWidth: SAFE_WIDTH,
          boxSizing: 'border-box',
          opacity,
          transform: `translateY(${(1 - enter) * -46}px) scale(${0.92 + 0.08 * enter})`,
        }}
      >
        <div
          style={{
            fontFamily: tokens.font,
            fontWeight: 800,
            fontSize: 52,
            color: tokens.accent,
            textAlign: 'center',
          }}
        >
          {title}
        </div>
        {items.map((item, i) => {
          const pop = spring({
            frame: Math.max(0, local - 10 - i * ITEM_STAGGER_F),
            fps,
            config: {damping: 13, stiffness: 170},
            durationInFrames: 16,
          });
          return (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                marginTop: i === 0 ? 22 : 14,
                opacity: pop,
                transform: `translateY(${(1 - pop) * 22}px)`,
              }}
            >
              <div
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: 4,
                  background: tokens.accent,
                  marginTop: 18,
                  marginRight: 18,
                  flexShrink: 0,
                }}
              />
              <div
                style={{
                  fontFamily: tokens.font,
                  fontWeight: 600,
                  fontSize: 40,
                  lineHeight: 1.35,
                  color: tokens.ink,
                }}
              >
                {item}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
