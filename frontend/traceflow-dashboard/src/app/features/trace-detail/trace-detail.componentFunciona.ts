import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { TraceService, Trace } from '../../core/services/trace.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableDataSource } from '@angular/material/table';

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
export class TraceDetailComponent implements OnInit {
  traceId: string;
  spans: Trace[] = [];
  dataSource = new MatTableDataSource<Trace>([]);
  loading = true;

  constructor(private route: ActivatedRoute, private traceService: TraceService) {
    this.traceId = this.route.snapshot.paramMap.get('id') || '';
  }

  ngOnInit(): void { this.loadTrace(); }

  loadTrace(): void {
    this.loading = true;
    this.traceService.getTraceDetail(this.traceId).subscribe({
      next: (data) => { 
      console.log('Datos recibidos:', data);
      this.spans = data;
      this.loading = false; 
      this.dataSource.data = data; 
      },
      error: () => this.loading = false
    });
  }

  goBack(): void { window.history.back(); }
}