import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Trace {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  service: string;
  duration_ms: number;
  status_code: number;
  created_at: string;
  data: any;
}

export interface MetricsResponse {
  total_traces: number;
  traces_last_hour: number;
  services: string[];
  traces_by_service: { service: string; count: number }[];  
}

@Injectable({ providedIn: 'root' })
export class TraceService {
  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getTraces(params?: any): Observable<Trace[]> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key]) httpParams = httpParams.set(key, params[key]);
      });
    }
    return this.http.get<Trace[]>(`${this.apiUrl}/traces/`, { params: httpParams });
  }

  getTraceDetail(traceId: string): Observable<Trace[]> {
    return this.http.get<Trace[]>(`${this.apiUrl}/traces/${traceId}/`);
  }

  getMetrics(): Observable<any> {
    return this.http.get<any>(`${this.apiUrl}/metrics/`);
  }

  getServices(): Observable<string[]> {
    return this.http.get<string[]>(`${this.apiUrl}/services/`);
  }

  getTracesPerService(): Observable<{name: string, count: number}[]> {
  return this.http.get<{name: string, count: number}[]>(`${this.apiUrl}/traces-per-service/`);
}
}