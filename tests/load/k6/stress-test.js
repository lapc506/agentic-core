import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const messageLatency = new Trend('ws_stress_latency', true);
const errors = new Counter('ws_stress_errors');

export const options = {
  stages: [
    { duration: '1m', target: 100 },
    { duration: '2m', target: 500 },   // stress beyond expected capacity
    { duration: '1m', target: 1000 },  // find breaking point
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    ws_stress_latency: ['p(95)<10000'],
    ws_stress_errors: ['rate<0.1'],      // <10% error rate under stress
  },
};

const WS_URL = __ENV.WS_URL || 'ws://localhost:8765';

export default function () {
  const res = ws.connect(WS_URL, {}, function (socket) {
    socket.on('open', function () {
      socket.send(JSON.stringify({
        type: 'create_session',
        persona_id: 'stress-agent',
        user_id: `stress_${__VU}_${__ITER}`,
      }));
    });

    socket.on('message', function (msg) {
      const data = JSON.parse(msg);
      if (data.type === 'session_created') {
        const start = Date.now();
        socket.send(JSON.stringify({
          type: 'message',
          session_id: data.session_id,
          persona_id: 'stress-agent',
          content: 'Stress test message',
        }));

        socket.on('message', function (reply) {
          const rd = JSON.parse(reply);
          if (rd.type === 'stream_end') {
            messageLatency.add(Date.now() - start);
            socket.close();
          }
          if (rd.type === 'error') errors.add(1);
        });
      }
    });

    socket.on('error', () => errors.add(1));
    socket.setTimeout(() => socket.close(), 15000);
  });

  check(res, { 'connected': (r) => r && r.status === 101 });
  sleep(0.5);
}
