enum ApiPlane {
  company,
  platform,
  agent,
  localWorker,
}

enum ApiDataState {
  populated,
  empty,
}

enum ApiFailureCode {
  unauthenticated,
  forbidden,
  notFound,
  invalidRequest,
  conflict,
  unavailable,
  notConnected,
  rateLimited,
  malformedResponse,
  unknown,
}

class ApiSourceRef {
  const ApiSourceRef({
    required this.kind,
    required this.ref,
    this.observedAt,
  });

  final String kind;
  final String ref;
  final DateTime? observedAt;

  factory ApiSourceRef.fromJson(Map<String, dynamic> json) {
    final kind = json['kind'];
    final ref = json['ref'];
    if (kind is! String || kind.isEmpty) {
      throw FormatException('Invalid or missing source ref kind: $kind');
    }
    if (ref is! String || ref.isEmpty) {
      throw FormatException('Invalid or missing source ref: $ref');
    }
    DateTime? obs;
    final obsStr = json['observed_at'] ?? json['observedAt'];
    if (obsStr is String && obsStr.isNotEmpty) {
      obs = DateTime.tryParse(obsStr);
      if (obs == null) {
        throw FormatException('Invalid source ref observed_at timestamp: $obsStr');
      }
    }
    return ApiSourceRef(
      kind: kind,
      ref: ref,
      observedAt: obs,
    );
  }

  Map<String, dynamic> toJson() => {
        'kind': kind,
        'ref': ref,
        if (observedAt != null) 'observed_at': observedAt!.toIso8601String(),
      };
}

class ApiResponseMeta {
  const ApiResponseMeta({
    required this.dataState,
    required this.observedAt,
    this.sources = const [],
  });

  final ApiDataState dataState;
  final DateTime observedAt;
  final List<ApiSourceRef> sources;

  factory ApiResponseMeta.fromJson(Map<String, dynamic> json) {
    final rawState = json['data_state'] ?? json['dataState'];
    final ApiDataState state;
    if (rawState == 'populated') {
      state = ApiDataState.populated;
    } else if (rawState == 'empty') {
      state = ApiDataState.empty;
    } else {
      throw FormatException('Invalid data_state: $rawState');
    }

    final rawObs = json['observed_at'] ?? json['observedAt'];
    if (rawObs is! String || rawObs.isEmpty) {
      throw FormatException('Missing observed_at timestamp in response meta');
    }
    final parsed = DateTime.tryParse(rawObs);
    if (parsed == null) {
      throw FormatException('Invalid observed_at timestamp: $rawObs');
    }

    final rawSources = json['sources'];
    final sourcesList = <ApiSourceRef>[];
    if (rawSources is List) {
      for (final item in rawSources) {
        if (item is Map<String, dynamic>) {
          sourcesList.add(ApiSourceRef.fromJson(item));
        } else {
          throw FormatException('Invalid source item: $item');
        }
      }
    }

    return ApiResponseMeta(
      dataState: state,
      observedAt: parsed,
      sources: sourcesList,
    );
  }
}

class ApiFailureDetail {
  const ApiFailureDetail({
    required this.code,
    this.statusCode,
    required this.message,
    this.retryAfter,
    this.endpointId,
    this.raw,
  });

  final ApiFailureCode code;
  final int? statusCode;
  final String message;
  final Duration? retryAfter;
  final String? endpointId;
  final Object? raw;

  @override
  String toString() =>
      'ApiFailureDetail(code: $code, statusCode: $statusCode, message: "$message", endpointId: $endpointId)';
}

sealed class ApiResult<T> {
  const ApiResult();

  bool get isSuccess => this is ApiSuccess<T>;
  bool get isFailure => this is ApiFailure<T>;

  T? get dataOrNull {
    final self = this;
    return self is ApiSuccess<T> ? self.data : null;
  }

  ApiFailureDetail? get failureOrNull {
    final self = this;
    return self is ApiFailure<T> ? self.failure : null;
  }

  R when<R>({
    required R Function(T data, ApiResponseMeta meta) success,
    required R Function(ApiFailureDetail failure) failure,
  }) {
    final self = this;
    if (self is ApiSuccess<T>) {
      return success(self.data, self.meta);
    } else if (self is ApiFailure<T>) {
      return failure(self.failure);
    }
    throw StateError('Unhandled ApiResult case');
  }
}

final class ApiSuccess<T> extends ApiResult<T> {
  const ApiSuccess({
    required this.data,
    required this.meta,
  });

  final T data;
  final ApiResponseMeta meta;

  T get value => data;

  @override
  String toString() =>
      'ApiSuccess(dataState: ${meta.dataState}, observedAt: ${meta.observedAt})';
}

final class ApiFailure<T> extends ApiResult<T> {
  const ApiFailure(this.failure);

  final ApiFailureDetail failure;

  @override
  String toString() => 'ApiFailure(${failure.toString()})';
}
