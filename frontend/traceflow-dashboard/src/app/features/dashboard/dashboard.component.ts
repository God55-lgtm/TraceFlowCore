import { Component, OnInit, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TraceService } from '../../core/services/trace.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import Chart from 'chart.js/auto';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css'],
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule]
})
export class DashboardComponent implements OnInit {
  @ViewChild('chartCanvas') chartCanvas!: ElementRef<HTMLCanvasElement>;
  chart: Chart | null = null;

  totalTraces = 0;
  tracesLastHour = 0;
  services: string[] = [];
  servicesData: { name: string; count: number }[] = [];
  loading = true;
  hasServices = false;

  constructor(private traceService: TraceService) {}

  ngOnInit(): void {
    this.loadMetrics();
    this.loadTracesPerService();
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.createChart(), 500);
  }

  loadMetrics(): void {
    this.traceService.getMetrics().subscribe({
      next: (data) => {
        this.totalTraces = data.total_traces;
        this.tracesLastHour = data.traces_last_hour;
        this.services = data.services || [];
        this.hasServices = this.services.length > 0;
        this.loading = false;
        this.updateChart();
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
        this.services = data.map(item => item.name);
        this.hasServices = this.services.length > 0;
        this.updateChart();
      },
      error: (err) => {
        console.error('Error cargando trazas por servicio:', err);
        // Si falla, usar datos simulados como respaldo
        if (this.services.length > 0) {
          this.servicesData = this.services.map(name => ({
            name,
            count: Math.floor(Math.random() * 100) + 1
          }));
          this.updateChart();
        }
      }
    });
  }

  createChart(): void {
    if (!this.chartCanvas) return;

    const labels = this.hasServices ? this.servicesData.map(d => d.name) : ['Sin datos'];
    const data = this.hasServices ? this.servicesData.map(d => d.count) : [0];
    const backgroundColor = this.hasServices ? '#3f51b5' : '#cccccc';

    if (this.chart) {
      this.chart.destroy();
    }

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
          y: { 
            beginAtZero: true,
            title: { display: true, text: 'Cantidad de trazas' }
          }
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
}