import { Component, OnInit, ViewChild, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TraceService, Trace } from '../../core/services/trace.service';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule, MatTableDataSource } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator } from '@angular/material/paginator';
import { MatSortModule, MatSort } from '@angular/material/sort';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-trace-list',
  templateUrl: './trace-list.component.html',
  styleUrls: ['./trace-list.component.css'],
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
  ]
})
export class TraceListComponent implements OnInit, OnDestroy {
  // Añadido 'path' a las columnas
  // displayedColumns: string[] = ['trace_id', 'service', 'path', 'duration_ms', 'status_code', 'created_at', 'actions'];
  displayedColumns: string[] = ['trace_id', 'service', 'path', 'duration_ms', 'status_code', 'created_at', 'client_ip', 'actions'];
  dataSource = new MatTableDataSource<Trace>([]);
  filterForm: FormGroup;
  loading = true;
  private refreshInterval: any;

  @ViewChild(MatPaginator) paginator!: MatPaginator;
  @ViewChild(MatSort) sort!: MatSort;

  constructor(
    private traceService: TraceService,
    private fb: FormBuilder,
    private router: Router
  ) {
    this.filterForm = this.fb.group({
      trace_id: [''],
      service: [''],
      path: [''],  // Nuevo filtro por path
      start_date: [''],
      end_date: [''],
      status_code: ['']
    });
  }

  ngOnInit(): void {
    this.loadTraces();
    // Actualizar cada 5 segundos
    this.refreshInterval = setInterval(() => {
      this.loadTraces();
    }, 5000);
  }

  ngAfterViewInit(): void {
    this.dataSource.paginator = this.paginator;
    this.dataSource.sort = this.sort;
  }

  ngOnDestroy(): void {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  loadTraces(): void {
    this.traceService.getTraces(this.filterForm.value).subscribe({
      next: (data) => {
        this.dataSource.data = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error cargando trazas:', err);
        this.loading = false;
      }
    });
  }

  applyFilter(): void {
    this.loading = true;
    this.traceService.getTraces(this.filterForm.value).subscribe({
      next: (data) => {
        this.dataSource.data = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error aplicando filtros:', err);
        this.loading = false;
      }
    });
  }

  resetFilter(): void {
    this.filterForm.reset();
    this.loadTraces();
  }

  viewTrace(traceId: string): void {
    this.router.navigate(['/traces', traceId]);
  }

  getStatusClass(status: number): string {
    if (status >= 200 && status < 300) return 'status-success';
    if (status >= 400 && status < 500) return 'status-client-error';
    if (status >= 500) return 'status-server-error';
    return '';
  }
}