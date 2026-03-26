import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const messageLatency = new Trend('ws_message_latency', true);
const errors = new Counter('ws_errors');

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // ramp up
    { duration: '1m', target: 50 },    // sustained load
    { duration: '30s', target: 100 },  // peak
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    ws_message_latency: ['p(99)<5000'],  // p99 < 5s
    ws_errors: ['count<10'],
  },
};

const WS_URL = __ENV.WS_URL || 'ws://localhost:8765';

export default function () {
  const res = ws.connect(WS_URL, {}, function (socket) {
    socket.on('open', function () {
      // Create session
      socket.send(JSON.stringify({
        type: 'create_session',
        persona_id: 'load-test-agent',
        user_id: `user_${__VU}`,
      }));
    });

    socket.on('message', function (msg) {
      const data = JSON.parse(msg);

      if (data.type === 'session_created') {
        const start = Date.now();

        // Send message
        socket.send(JSON.stringify({
          type: 'message',
          session_id: data.session_id,
          persona_id: 'load-test-agent',
          content: 'Hello from k6 load test',
        }));

        socket.on('message', function (reply) {
          const replyData = JSON.parse(reply);
          if (replyData.type === 'stream_end') {
            messageLatency.add(Date.now() - start);
            socket.send(JSON.stringify({
              type: 'close_session',
              session_id: data.session_id,
            }));
          }
          if (replyData.type === 'error') {
            errors.add(1);
          }
        });
      }
    });

    socket.on('error', function (e) {
      errors.add(1);
    });

    socket.setTimeout(function () {
      socket.close();
    }, 10000);
  });

  check(res, { 'status is 101': (r) => r && r.status === 101 });
  sleep(1);
}
