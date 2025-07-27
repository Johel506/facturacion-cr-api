#!/usr/bin/env python3
"""
Master Seeding Script

This script runs all seeding scripts in the correct order to populate
the database with reference data and sample development data for the
Costa Rica Electronic Invoice API.

Requirements: 11.2, 12.1, 17.1, 18.3
"""
import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MasterSeeder:
    """Master seeding utility that runs all seeding scripts"""
    
    def __init__(self, scripts_dir: Path = None):
        """
        Initialize the master seeder
        
        Args:
            scripts_dir: Directory containing seeding scripts
        """
        self.scripts_dir = scripts_dir or Path(__file__).parent
        self.python_executable = sys.executable
    
    def run_script(self, script_name: str, args: List[str] = None) -> Dict[str, any]:
        """
        Run a seeding script
        
        Args:
            script_name: Name of the script to run (without .py extension)
            args: Additional arguments to pass to the script
            
        Returns:
            Dictionary with execution results
        """
        script_path = self.scripts_dir / f"{script_name}.py"
        
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        
        cmd = [self.python_executable, str(script_path)]
        if args:
            cmd.extend(args)
        
        logger.info(f"Running script: {script_name} with args: {args or []}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            return {
                'script': script_name,
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"Script {script_name} timed out")
            return {
                'script': script_name,
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Script execution timed out'
            }
        except Exception as e:
            logger.error(f"Error running script {script_name}: {str(e)}")
            return {
                'script': script_name,
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def seed_reference_data(self, clear_existing: bool = False, use_excel: bool = False) -> Dict[str, any]:
        """
        Seed all reference data in the correct order
        
        Args:
            clear_existing: Whether to clear existing data first
            use_excel: Whether to use Excel files for data (if available)
            
        Returns:
            Dictionary with results from all scripts
        """
        logger.info("Starting reference data seeding...")
        
        results = {}
        
        # Define seeding order and scripts
        seeding_steps = [
            {
                'name': 'units',
                'script': 'seed_units',
                'description': 'Units of Measure (RTC 443:2010)',
                'args': ['--clear'] if clear_existing else []
            },
            {
                'name': 'locations',
                'script': 'seed_locations',
                'description': 'Costa Rican Geographic Locations',
                'args': (['--clear'] if clear_existing else []) + 
                       (['--excel', 'Estructuras XML y Anexos Version 4.4/Codificacionubicacion_V4.4.xlsx'] if use_excel else [])
            },
            {
                'name': 'cabys',
                'script': 'seed_cabys',
                'description': 'CABYS Product Classification Codes',
                'args': (['--clear'] if clear_existing else []) + 
                       (['--sample'] if not use_excel else [])
            }
        ]
        
        # Execute seeding steps
        for step in seeding_steps:
            logger.info(f"Seeding {step['description']}...")
            
            result = self.run_script(step['script'], step['args'])
            results[step['name']] = result
            
            if result['success']:
                logger.info(f"✓ {step['description']} seeded successfully")
                if result['stdout']:
                    # Log key information from stdout
                    for line in result['stdout'].split('\n'):
                        if 'Successfully created' in line or 'completed successfully' in line:
                            logger.info(f"  {line.strip()}")
            else:
                logger.error(f"✗ Failed to seed {step['description']}")
                logger.error(f"  Return code: {result['returncode']}")
                if result['stderr']:
                    logger.error(f"  Error: {result['stderr']}")
                
                # Continue with other steps even if one fails
                continue
        
        return results
    
    def seed_development_data(self, clear_existing: bool = False) -> Dict[str, any]:
        """
        Seed development sample data
        
        Args:
            clear_existing: Whether to clear existing sample data first
            
        Returns:
            Dictionary with results from development data seeding
        """
        logger.info("Starting development data seeding...")
        
        args = []
        if clear_existing:
            args.append('--clear')
        else:
            args.append('--all')
        
        result = self.run_script('seed_dev_data', args)
        
        if result['success']:
            logger.info("✓ Development data seeded successfully")
            if result['stdout']:
                # Log key information from stdout
                for line in result['stdout'].split('\n'):
                    if 'API Key:' in line or 'Created' in line or 'completed successfully' in line:
                        logger.info(f"  {line.strip()}")
        else:
            logger.error("✗ Failed to seed development data")
            logger.error(f"  Return code: {result['returncode']}")
            if result['stderr']:
                logger.error(f"  Error: {result['stderr']}")
        
        return {'dev_data': result}
    
    def seed_all(self, clear_existing: bool = False, use_excel: bool = False, 
                 include_dev_data: bool = True) -> Dict[str, any]:
        """
        Run complete seeding process
        
        Args:
            clear_existing: Whether to clear existing data first
            use_excel: Whether to use Excel files for data (if available)
            include_dev_data: Whether to include development sample data
            
        Returns:
            Dictionary with results from all seeding operations
        """
        logger.info("Starting complete database seeding process...")
        
        all_results = {}
        
        try:
            # Seed reference data first
            ref_results = self.seed_reference_data(clear_existing, use_excel)
            all_results.update(ref_results)
            
            # Seed development data if requested
            if include_dev_data:
                dev_results = self.seed_development_data(clear_existing)
                all_results.update(dev_results)
            
            # Summary
            successful_steps = sum(1 for result in all_results.values() if result['success'])
            total_steps = len(all_results)
            
            logger.info(f"Seeding process completed: {successful_steps}/{total_steps} steps successful")
            
            if successful_steps == total_steps:
                logger.info("🎉 All seeding operations completed successfully!")
            else:
                logger.warning(f"⚠️  {total_steps - successful_steps} seeding operations failed")
            
        except Exception as e:
            logger.error(f"Error in master seeding process: {str(e)}")
            all_results['master_error'] = {
                'script': 'seed_all',
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }
        
        return all_results
    
    def print_summary(self, results: Dict[str, any]):
        """
        Print a summary of seeding results
        
        Args:
            results: Results dictionary from seeding operations
        """
        print("\n" + "="*80)
        print("DATABASE SEEDING SUMMARY")
        print("="*80)
        
        for step_name, result in results.items():
            status = "✓ SUCCESS" if result['success'] else "✗ FAILED"
            print(f"{step_name.upper():20} | {status}")
            
            if not result['success'] and result['stderr']:
                print(f"{'':20} | Error: {result['stderr'][:50]}...")
        
        print("="*80)
        
        successful = sum(1 for r in results.values() if r['success'])
        total = len(results)
        print(f"Overall: {successful}/{total} operations successful")
        
        if successful == total:
            print("🎉 Database seeding completed successfully!")
            print("\nYou can now start the API server and begin development.")
        else:
            print("⚠️  Some seeding operations failed. Check the logs above.")
        
        print("="*80 + "\n")


def main():
    """Main function to run master seeding"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Master database seeding script')
    parser.add_argument('--clear', action='store_true', 
                       help='Clear existing data before seeding')
    parser.add_argument('--excel', action='store_true',
                       help='Use Excel files for data (if available)')
    parser.add_argument('--no-dev-data', action='store_true',
                       help='Skip development sample data seeding')
    parser.add_argument('--reference-only', action='store_true',
                       help='Seed only reference data (CABYS, locations, units)')
    parser.add_argument('--dev-only', action='store_true',
                       help='Seed only development sample data')
    parser.add_argument('--summary', action='store_true',
                       help='Show detailed summary at the end')
    
    args = parser.parse_args()
    
    # Initialize master seeder
    seeder = MasterSeeder()
    
    try:
        if args.reference_only:
            # Seed only reference data
            results = seeder.seed_reference_data(args.clear, args.excel)
        elif args.dev_only:
            # Seed only development data
            results = seeder.seed_development_data(args.clear)
        else:
            # Seed everything
            results = seeder.seed_all(
                clear_existing=args.clear,
                use_excel=args.excel,
                include_dev_data=not args.no_dev_data
            )
        
        # Show summary if requested
        if args.summary:
            seeder.print_summary(results)
        
        # Exit with appropriate code
        failed_operations = sum(1 for r in results.values() if not r['success'])
        if failed_operations > 0:
            logger.error(f"Seeding completed with {failed_operations} failures")
            sys.exit(1)
        else:
            logger.info("All seeding operations completed successfully")
            sys.exit(0)
        
    except Exception as e:
        logger.error(f"Master seeding failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()