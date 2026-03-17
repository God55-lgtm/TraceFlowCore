import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { Router } from '@angular/router';  // ← Importar Router
import { environment } from '../../../environments/environment';
import { JwtHelperService } from '@auth0/angular-jwt';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'access_token';
  private readonly REFRESH_KEY = 'refresh_token';
  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();
  private jwtHelper = new JwtHelperService();

  constructor(
    private http: HttpClient,
    private router: Router  // ← Inyectar Router
  ) {
    this.loadUserFromToken();
  }

  login(username: string, password: string): Observable<any> {
    return this.http.post<any>(environment.tokenUrl, { username, password }).pipe(
      tap(response => {
        this.setTokens(response.access, response.refresh);
        this.loadUserFromToken();
      })
    );
  }

  refreshToken(): Observable<any> {
    const refresh = this.getRefreshToken();
    return this.http.post<any>(environment.refreshTokenUrl, { refresh }).pipe(
      tap(response => this.setAccessToken(response.access))
    );
  }

  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    this.currentUserSubject.next(null);
    this.router.navigate(['/login']);  // ← Redirigir al login
  }

  getAccessToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_KEY);
  }

  isAuthenticated(): boolean {
    const token = this.getAccessToken();
    return token ? !this.jwtHelper.isTokenExpired(token) : false;
  }

  private setTokens(access: string, refresh: string): void {
    localStorage.setItem(this.TOKEN_KEY, access);
    localStorage.setItem(this.REFRESH_KEY, refresh);
  }

  private setAccessToken(access: string): void {
    localStorage.setItem(this.TOKEN_KEY, access);
  }

  private loadUserFromToken(): void {
    const token = this.getAccessToken();
    if (token && !this.jwtHelper.isTokenExpired(token)) {
      const decoded = this.jwtHelper.decodeToken(token);
      this.currentUserSubject.next(decoded);
    }
  }
}