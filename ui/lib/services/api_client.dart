import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:logging/logging.dart';

class ApiClient {
  static final _log = Logger('ApiClient');
  ApiClient({String? baseUrl}) : _baseUrl = baseUrl ?? _defaultBaseUrl();
  final String _baseUrl;

  /// Resolve base URL for API calls. Web uses relative, desktop uses localhost.
  static String _defaultBaseUrl() {
    try {
      final uri = Uri.base;
      if (uri.scheme == 'http' || uri.scheme == 'https') {
        return ''; // Web — relative URLs work
      }
    } catch (_) {}
    return 'http://localhost:8080'; // Desktop/mobile fallback
  }

  /// Global base URL accessible by other files that make direct HTTP calls.
  static String get baseUrl => _defaultBaseUrl();

  Future<Map<String, dynamic>> health() async {
    _log.fine('GET /api/health');
    final resp = await http.get(Uri.parse('$_baseUrl/api/health'));
    _log.fine('health: ${resp.statusCode} (${resp.body.length} bytes)');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listAgents() async {
    _log.fine('GET /api/agents');
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents'));
    _log.fine('listAgents: ${resp.statusCode} (${resp.body.length} bytes)');
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getAgent(String slug) async {
    _log.fine('GET /api/agents/$slug');
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug'));
    _log.fine('getAgent($slug): ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createAgent(Map<String, dynamic> data) async {
    _log.fine('POST /api/agents');
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/agents'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    _log.fine('createAgent: ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAgent(String slug, Map<String, dynamic> data) async {
    _log.fine('PUT /api/agents/$slug');
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    _log.fine('updateAgent($slug): ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteAgent(String slug) async {
    _log.fine('DELETE /api/agents/$slug');
    await http.delete(Uri.parse('$_baseUrl/api/agents/$slug'));
    _log.fine('deleteAgent($slug): done');
  }

  Future<List<dynamic>> getGates(String slug) async {
    _log.fine('GET /api/agents/$slug/gates');
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug/gates'));
    _log.fine('getGates($slug): ${resp.statusCode}');
    return jsonDecode(resp.body) as List;
  }

  Future<List<dynamic>> updateGates(String slug, List<Map<String, dynamic>> gates) async {
    _log.fine('PUT /api/agents/$slug/gates (${gates.length} gates)');
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug/gates'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'gates': gates}),
    );
    _log.fine('updateGates($slug): ${resp.statusCode}');
    return jsonDecode(resp.body) as List;
  }

  Future<Map<String, dynamic>> getMetrics(String metricType, {String window = '1h'}) async {
    _log.fine('GET /api/metrics/$metricType?window=$window');
    final resp = await http.get(Uri.parse('$_baseUrl/api/metrics/$metricType?window=$window'));
    _log.fine('getMetrics($metricType): ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listTools() async {
    _log.fine('GET /api/tools');
    final resp = await http.get(Uri.parse('$_baseUrl/api/tools'));
    _log.fine('listTools: ${resp.statusCode} (${resp.body.length} bytes)');
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> listSessions() async {
    _log.fine('GET /api/sessions');
    final resp = await http.get(Uri.parse('$_baseUrl/api/sessions'));
    _log.fine('listSessions: ${resp.statusCode} (${resp.body.length} bytes)');
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getConfig() async {
    _log.fine('GET /api/config');
    final resp = await http.get(Uri.parse('$_baseUrl/api/config'));
    _log.fine('getConfig: ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDockerStatus() async {
    _log.fine('GET /api/docker/status');
    final resp = await http.get(Uri.parse('$_baseUrl/api/docker/status'));
    _log.fine('getDockerStatus: ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getStudioConfig() async {
    _log.fine('GET /api/studio/config');
    final resp = await http.get(Uri.parse('$_baseUrl/api/studio/config'));
    _log.fine('getStudioConfig: ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> saveStudioConfig(Map<String, dynamic> config) async {
    _log.fine('POST /api/studio/config');
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/studio/config'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(config),
    );
    _log.fine('saveStudioConfig: ${resp.statusCode}');
  }

  /// Generic POST for arbitrary endpoints (used by GenUI transport).
  Future<Map<String, dynamic>> rawPost(String path, Map<String, dynamic> body) async {
    _log.fine('POST $path');
    final resp = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    _log.fine('rawPost($path): ${resp.statusCode}');
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }
}
