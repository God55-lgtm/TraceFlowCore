import { Component, OnInit, AfterViewInit, ElementRef, ViewChild } from '@angular/core';
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

  @ViewChild('graphContainer') graphContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('waterfallCanvas') waterfallCanvas!: ElementRef<HTMLCanvasElement>;

  private chart: Chart | null = null;
  private svg: any = null;
  private zoom: any = null;

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

  ngAfterViewInit(): void {}

  loadTrace(): void {
    this.loading = true;
    this.traceService.getTraceDetail(this.traceId).subscribe({
      next: (data) => {
        console.log('Datos recibidos:', data);
        this.spans = data;
        this.dataSource.data = data;
        this.loading = false;
        // Esperar a que el DOM se estabilice
        setTimeout(() => {
          this.drawGraph();
          this.drawWaterfall();
        }, 500);
      },
      error: (err) => {
        console.error('Error cargando traza:', err);
        this.loading = false;
      }
    });
  }

  drawGraph(): void {
    if (!this.spans.length) return;

    const container = this.graphContainer?.nativeElement;
    if (!container) {
      console.warn('Contenedor del grafo no encontrado');
      return;
    }

    container.innerHTML = '';
    const width = container.clientWidth;
    const height = container.clientHeight;

    if (width === 0 || height === 0) {
      console.warn('El contenedor del grafo aún no tiene dimensiones, reintentando...');
      setTimeout(() => this.drawGraph(), 200);
      return;
    }

    this.svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .append('g');

    this.zoom = d3.zoom()
      .scaleExtent([0.2, 3])
      .on('zoom', (event) => {
        this.svg.attr('transform', event.transform);
      });
    d3.select(container).select('svg').call(this.zoom);

    const nodesMap = new Map<string, any>();
    const edges: { source: string; target: string }[] = [];

    this.spans.forEach(span => {
      nodesMap.set(span.span_id, {
        id: span.span_id,
        name: span.service,
        duration: span.duration_ms,
        status: span.status_code,
        path: span.data?.path || '-'
      });
    });

    this.spans.forEach(span => {
      if (span.parent_span_id && nodesMap.has(span.parent_span_id)) {
        edges.push({ source: span.parent_span_id, target: span.span_id });
      }
    });

    if (edges.length === 0 && this.spans.length === 1) {
      this.svg.append('text')
        .attr('x', width / 2)
        .attr('y', height / 2)
        .attr('text-anchor', 'middle')
        .attr('font-size', '14px')
        .text('Único span (sin relaciones padre-hijo)');
      return;
    }

    const nodes = Array.from(nodesMap.values());
    const links = edges.map(e => ({ source: e.source, target: e.target }));

    const simulation = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links).id((d: any) => d.id).distance(150))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(40));

    const link = this.svg.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter()
      .append('line')
      .attr('stroke', '#999')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6);

    const node = this.svg.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter()
      .append('g')
      .call(d3.drag<any, any>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          (d as any).fx = d.x;
          (d as any).fy = d.y;
        })
        .on('drag', (event, d) => {
          (d as any).fx = event.x;
          (d as any).fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          (d as any).fx = null;
          (d as any).fy = null;
        }));

    node.append('circle')
      .attr('r', 25)
      .attr('fill', (d: any) => {
        if (d.status >= 500) return '#f44336';
        if (d.status >= 400) return '#ff9800';
        return '#3f51b5';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 2);

    node.append('text')
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('fill', '#fff')
      .text((d: any) => d.name);

    node.append('title')
      .text((d: any) => `${d.name}\nRuta: ${d.path}\nDuración: ${d.duration}ms\nEstado: ${d.status}`);

    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);
      node.attr('transform', (d: any) => `translate(${d.x},${d.y})`);
    });

    setTimeout(() => {
      const svgElem = d3.select(container).select('svg');
      const bounds = (svgElem.node() as any).getBBox();
      if (bounds.width > 0 && bounds.height > 0) {
        const scale = Math.min(width / bounds.width, height / bounds.height) * 0.8;
        const transform = d3.zoomIdentity
          .translate(width / 2, height / 2)
          .scale(scale)
          .translate(-(bounds.x + bounds.width / 2), -(bounds.y + bounds.height / 2));
        svgElem.call(this.zoom.transform, transform);
      }
    }, 500);
  }

  drawWaterfall(): void {
    if (!this.spans.length) return;

    const canvas = this.waterfallCanvas?.nativeElement;
    if (!canvas) return;

    if (this.chart) this.chart.destroy();

    // Ordenar por timestamp real (fallback a created_at)
    const sortedSpans = [...this.spans].sort((a, b) => {
      const timeA = a.data?.timestamp ?? new Date(a.created_at).getTime();
      const timeB = b.data?.timestamp ?? new Date(b.created_at).getTime();
      return timeA - timeB;
    });

    const labels = sortedSpans.map(s => `${s.service} - ${s.data?.path || s.span_id.substring(0, 8)}`);
    const durations = sortedSpans.map(s => s.duration_ms);
    const colors = sortedSpans.map(s => {
      if (s.status_code >= 500) return '#f44336';
      if (s.status_code >= 400) return '#ff9800';
      return '#3f51b5';
    });

    this.chart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Duración (ms)',
          data: durations,
          backgroundColor: colors,
          borderRadius: 4,
          barPercentage: 0.6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const span = sortedSpans[context.dataIndex];
                return [
                  `Servicio: ${span.service}`,
                  `Ruta: ${span.data?.path || '-'}`,
                  `Duración: ${span.duration_ms} ms`,
                  `Estado: ${span.status_code}`,
                  `Span ID: ${span.span_id}`,
                  `Parent: ${span.parent_span_id || 'raíz'}`
                ];
              }
            }
          }
        },
        scales: {
          x: { title: { display: true, text: 'Duración (ms)', font: { weight: 'bold' } }, beginAtZero: true },
          y: { title: { display: true, text: 'Operaciones', font: { weight: 'bold' } }, ticks: { autoSkip: false, font: { size: 10 } } }
        }
      }
    });
  }

  getStatusClass(status: number): string {
    if (status >= 200 && status < 300) return 'status-success';
    if (status >= 400 && status < 500) return 'status-client-error';
    if (status >= 500) return 'status-server-error';
    return '';
  }

  goBack(): void {
    window.history.back();
  }
}