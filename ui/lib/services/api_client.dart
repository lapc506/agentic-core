import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiClient {
  ApiClient({String? baseUrl}) : _baseUrl = baseUrl ?? '';
  final String _baseUrl;

  Future<Map<String, dynamic>> health() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/health'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listAgents() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents'));
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getAgent(String slug) async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createAgent(Map<String, dynamic> data) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl/api/agents'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateAgent(String slug, Map<String, dynamic> data) async {
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(data),
    );
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteAgent(String slug) async {
    await http.delete(Uri.parse('$_baseUrl/api/agents/$slug'));
  }

  Future<List<dynamic>> getGates(String slug) async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/agents/$slug/gates'));
    return jsonDecode(resp.body) as List;
  }

  Future<List<dynamic>> updateGates(String slug, List<Map<String, dynamic>> gates) async {
    final resp = await http.put(
      Uri.parse('$_baseUrl/api/agents/$slug/gates'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'gates': gates}),
    );
    return jsonDecode(resp.body) as List;
  }

  Future<Map<String, dynamic>> getMetrics(String metricType, {String window = '1h'}) async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/metrics/$metricType?window=$window'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listTools() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/tools'));
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<List<Map<String, dynamic>>> listSessions() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/sessions'));
    final list = jsonDecode(resp.body) as List;
    return list.cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> getConfig() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/config'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getDockerStatus() async {
    final resp = await http.get(Uri.parse('$_baseUrl/api/docker/status'));
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  /// Generic POST for arbitrary endpoints (used by GenUI transport).
  Future<Map<String, dynamic>> rawPost(String path, Map<String, dynamic> body) async {
    final resp = await http.post(
      Uri.parse('$_baseUrl$path'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(body),
    );
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }
}
