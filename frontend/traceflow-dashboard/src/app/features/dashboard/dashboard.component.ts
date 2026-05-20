import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TraceService } from '../../core/services/trace.service';
import { AuthService } from '../../core/services/auth.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatInputModule } from '@angular/material/input';
import Chart from 'chart.js/auto';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatInputModule
  ]
})
export class DashboardComponent implements OnInit {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  chart: Chart | null = null;

  totalTraces = 0;
  tracesLastHour = 0;
  servicesData: { name: string; count: number }[] = [];
  hasServices = false;
  loading = true;

  // Purga
  purgeDate: Date | null = null;
  purging = false;
  purgeResult: { success: boolean; message: string } | null = null;
  isAdmin = false;

  constructor(
    private traceService: TraceService,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.loadMetrics();
    this.loadTracesPerService();
    this.checkAdminRole();
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.createChart(), 500);
  }

  checkAdminRole(): void {
    const token = this.authService.getAccessToken();
    if (token) {
      try {       
        const payload = JSON.parse(atob(token.split('.')[1]));
        
        // Ajusta según el campo que use tu backend: role, groups, is_staff, etc.
        this.isAdmin = true
      } catch (e) {
        console.error('Error decodificando token', e);
      }
    }
  }

  loadMetrics(): void {
    this.traceService.getMetrics().subscribe({
      next: (data) => {
        this.totalTraces = data.total_traces;
        this.tracesLastHour = data.traces_last_hour;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error cargando métricas:', err);
        this.loading = false;
      }
    });
  }

  loadTracesPerService(): void {
    this.traceService.getTracesPerService().subscribe({
      next: (data) => {
        this.servicesData = data;
        this.hasServices = this.servicesData.length > 0;
        this.updateChart();
      },
      error: (err) => {
        console.error('Error cargando trazas por servicio:', err);
        this.hasServices = false;
        this.updateChart();
      }
    });
  }

  createChart(): void {
    if (!this.chartCanvas) return;

    const labels = this.hasServices ? this.servicesData.map(d => d.name) : ['Sin datos'];
    const data = this.hasServices ? this.servicesData.map(d => d.count) : [0];
    const backgroundColor = this.hasServices ? '#3f51b5' : '#cccccc';

    if (this.chart) this.chart.destroy();

    this.chart = new Chart(this.chartCanvas.nativeElement, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Trazas por servicio',
          data: data,
          backgroundColor: backgroundColor,
          borderRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                if (!this.hasServices) return 'No hay servicios disponibles';
                const item = this.servicesData[context.dataIndex];
                return `${item.name}: ${item.count} trazas`;
              }
            }
          }
        },
        scales: {
          y: { beginAtZero: true, title: { display: true, text: 'Cantidad de trazas' } }
        }
      }
    });
  }

  updateChart(): void {
    if (this.chart) {
      if (this.hasServices && this.servicesData.length > 0) {
        this.chart.data.labels = this.servicesData.map(d => d.name);
        this.chart.data.datasets[0].data = this.servicesData.map(d => d.count);
        this.chart.data.datasets[0].backgroundColor = '#3f51b5';
      } else {
        this.chart.data.labels = ['Sin servicios'];
        this.chart.data.datasets[0].data = [0];
        this.chart.data.datasets[0].backgroundColor = '#cccccc';
      }
      this.chart.update();
    } else {
      setTimeout(() => this.createChart(), 100);
    }
  }

  purgeTraces(): void {
    if (!this.purgeDate) return;
    const formattedDate = this.purgeDate.toISOString().split('T')[2];
    if (!confirm(`¿Eliminar permanentemente todas las trazas anteriores a ${formattedDate}? Esta acción no se puede deshacer.`)) {
      return;
    }

    this.purging = true;
    this.purgeResult = null;

    this.traceService.purgeTraces(formattedDate).subscribe({
      next: (res) => {
        this.purging = false;
        this.purgeResult = { success: true, message: `Se eliminaron ${res.deleted} trazas correctamente.` };
        this.loadMetrics();
        this.loadTracesPerService();
        
      },
      error: (err) => {
        this.purging = false;
        const msg = err.error?.error || 'Error al purgar trazas. Intente de nuevo.';
        this.purgeResult = { success: false, message: msg };
        console.error('Error en purga:', err);
      }
    });
  }
}