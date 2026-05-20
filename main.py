import os
import datetime

# Directorios y extensiones a incluir (ajusta según tu proyecto)
INCLUDE_DIRS = ['backend', 'frontend', 'microservicios', 'database', 'scripts']
EXTENSIONS = ('.py', '.js', '.ts', '.html', '.css', '.json', '.sql', '.ps1', '.sh', '.md', '.txt')
EXCLUDE_DIRS = ['__pycache__', 'node_modules', '.git', 'venv', 'env', 'dist', 'build']

def should_include(filepath):
    # Excluir directorios no deseados
    for exclude in EXCLUDE_DIRS:
        if exclude in filepath.split(os.sep):
            return False
    return filepath.endswith(EXTENSIONS)

def generate_export(root_dir):
    output_file = 'project_export.txt'
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"# Exportación completa del proyecto TraceFlowCore\n")
        out.write(f"# Generado: {datetime.datetime.now().isoformat()}\n\n")
        
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Modificar dirnames in-place para excluir directorios
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                relpath = os.path.relpath(filepath, root_dir)
                
                if should_include(filepath):
                    out.write(f"\n{'='*80}\n")
                    out.write(f"ARCHIVO: {relpath}\n")
                    out.write(f"{'='*80}\n\n")
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            out.write(f.read())
                    except Exception as e:
                        out.write(f"// ERROR al leer archivo: {e}\n")
                    
    print(f"Exportación completada. Revisa el archivo: {output_file}")

if __name__ == "__main__":
    generate_export(os.getcwd())