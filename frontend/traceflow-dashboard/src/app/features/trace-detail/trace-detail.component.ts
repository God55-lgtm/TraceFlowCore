import { Component, OnInit, AfterViewInit, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { TraceService, Trace } from '../../core/services/trace.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableDataSource } from '@angular/material/table';
import * as d3 from 'd3';
import Chart from 'chart.js/auto';

@Component({
  selector: 'app-trace-detail',
  templateUrl: './trace-detail.component.html',
  styleUrls: ['./trace-detail.component.css'],
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    MatProgressSpinnerModule,
  ]
})
export class TraceDetailComponent implements OnInit, AfterViewInit {
  traceId: string;
  spans: Trace[] = [];
  dataSource = new MatTableDataSource<Trace>([]);
  loading = true;

  constructor(
    private route: ActivatedRoute,
    private traceService: TraceService,
    private el: ElementRef
  ) {
    this.traceId = this.route.snapshot.paramMap.get('id') || '';
  }

  ngOnInit(): void {
    this.loadTrace();
  }

  ngAfterViewInit(): void {
    // Se dibujará después de cargar los datos
  }

  loadTrace(): void {
    this.loading = true;
    this.traceService.getTraceDetail(this.traceId).subscribe({
      next: (data) => {
        console.log('Datos recibidos:', data);
        this.spans = data;
        this.dataSource.data = data;
        this.loading = false;
        // Dibujar después de que el DOM esté listo
        setTimeout(() => {
          this.drawGraph();
          this.drawWaterfall();
        }, 100);
      },
      error: () => this.loading = false
    });
  }

  drawGraph(): void {
    if (!this.spans.length) return;

    const element = this.el.nativeElement.querySelector('#graph-container');
    if (!element) return;

    element.innerHTML = ''; // Limpiar

    const width = element.clientWidth;
    const height = 500;

    const svg = d3.select(element)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    // Crear nodos y aristas
    const nodes: any[] = this.spans.map(span => ({
      id: span.span_id,
      name: `${span.service} (${span.duration_ms}ms)`,
      group: span.service
    }));

    const edges: any[] = this.spans
      .filter(span => span.parent_span_id)
      .map(span => ({
        source: span.parent_span_id,
        target: span.span_id
      }));

    // Construir jerarquía
    const stratify = d3.stratify()
      .id((d: any) => d.id)
      .parentId((d: any) => {
        const edge = edges.find(e => e.target === d.id);
        return edge ? edge.source : null;
      });

    try {
      const root: any = stratify(nodes);
      const tree = d3.tree().size([height - 100, width - 200]);
      tree(root);

      // Dibujar aristas
      svg.selectAll('.edge')
        .data(root.links())
        .enter()
        .append('line')
        .attr('class', 'edge')
        .attr('x1', (d: any) => (d.source.y || 0) + 100)
        .attr('y1', (d: any) => d.source.x || 0)
        .attr('x2', (d: any) => (d.target.y || 0) + 100)
        .attr('y2', (d: any) => d.target.x || 0)
        .attr('stroke', '#999')
        .attr('stroke-width', 1.5);

      // Dibujar nodos
      const node = svg.selectAll('.node')
        .data(root.descendants())
        .enter()
        .append('g')
        .attr('class', 'node')
        .attr('transform', (d: any) => `translate(${(d.y || 0) + 100},${d.x || 0})`);

      node.append('circle')
        .attr('r', 10)
        .attr('fill', (d: any) => {
          const span = this.spans.find(s => s.span_id === d.id);
          return span?.status_code && span.status_code >= 400 ? '#f44336' : '#3f51b5';
        });

      node.append('text')
        .attr('dy', '0.31em')
        .attr('x', 15)
        .attr('font-size', '10px')
        .text((d: any) => d.data.name);
    } catch (e) {
      console.error('Error al dibujar grafo:', e);
    }
  }

  drawWaterfall(): void {
    if (!this.spans.length) return;

    const canvas = this.el.nativeElement.querySelector('#waterfallCanvas');
    if (!canvas) return;

    // Ordenar spans por timestamp
    const sortedSpans = [...this.spans].sort((a, b) => a.data.timestamp - b.data.timestamp);
    const labels = sortedSpans.map(s => `${s.service} - ${s.data?.path || s.span_id.substring(0, 8)}`);
    const data = sortedSpans.map(s => s.duration_ms);
    const colors = sortedSpans.map(s => s.status_code >= 400 ? '#f44336' : '#3f51b5');

    new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Duración (ms)',
          data: data,
          backgroundColor: colors,
          borderRadius: 4
        }]
      },
      options: {
        indexAxis: 'y',  // Barras horizontales (waterfall)
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const span = sortedSpans[context.dataIndex];
                return `${span.service} - ${span.data?.path || ''} - ${span.duration_ms}ms`;
              }
            }
          }
        },
        scales: {
          x: { title: { display: true, text: 'Duración (ms)' } }
        }
      }
    });
  }

  goBack(): void {
    window.history.back();
  }
}