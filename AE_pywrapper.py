# ADRIANA ESPARZA LUC COMPBIO 483 
# This python wrapper script takes samples of 2 donors and a total of 4 transcriptomes.
# The command-line used was the following (but may vary based on sample input data): python AE_pywrapper.py HCMVINDEX 30sample_reads.1.fastq 30sample_reads.2.fastq 33sample_reads.1.fastq 33sample_reads.2.fastq 44sample_reads.1.fastq 44sample_reads.2.fastq 45sample_reads.1.fastq 45sample_reads.2.fastq
# The code expects the command-line to provide the script's name, a previously created index (in this case for HCMV NCBI accession NC_006273.2), and 8 paired-end files (based on the 4 transcriptomes split in fastq format. Each is less than 1MB)
# Error comments and exits were added just to identify issues while building this script

import sys
import os
import subprocess

# To solve PART 2, MAPPING TO INDEX WITH BOWTIE2 AND COUNTING BEFORE/AFTER READS
def count_aligned_reads(sam_file, mapq_threshold=20): # To count the reads in sam files above a mapq score of 20 *for a 99% confidence level
    aligned_reads = 0
    with open(sam_file, 'r') as f:
        for line in f:
            if line.startswith('@'):
                continue  # To skip header lines containing @
            parts = line.split('\t')
            mapq = int(parts[4])  # Since MAPQ is the fifth field in SAM format this will detect it
            if mapq >= mapq_threshold:
                aligned_reads += 1
    return aligned_reads

def run_bowtie2_and_count_reads(read_file_1, read_file_2, index_prefix): # To calculate the reads before alignment from a FASTQ file (counts lines and divides by 4)
    total_reads_before = sum(1 for line in open(read_file_1)) // 4
    total_reads_before += sum(1 for line in open(read_file_2)) // 4

    sam_output = f"{os.path.splitext(read_file_1)[0]}_bowtie2.sam" # To create a command to align the reads to the index. It then saves the outputs in .sam files
    unaligned_output_base = os.path.splitext(read_file_1)[0] + "_unaligned" # To separate the unaligned reads in a different file

    # To run Bowtie2
    bowtie2_cmd = [
        "bowtie2",
        "-x", index_prefix, # To identify my index and use it to search for alignment locations
        "-1", read_file_1, # To specify that the sample files provided are paired-end
        "-2", read_file_2, # Same here but for the .2s files
        "--un-conc", f"{unaligned_output_base}%.fastq", # To separate the unaligned reads from the aligned ones
        "-S", sam_output # o output the files in the regularly used sam format
    ]

    try:
        subprocess.run(bowtie2_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Bowtie2: {e}")
        sys.exit(1)  # To make the code exit if Bowtie2 fails

    aligned_reads = count_aligned_reads(sam_output, mapq_threshold=20) # To count the aligned reads from the .sam files

    return total_reads_before, aligned_reads

def process_paired_end_reads(read_files, index_prefix): # This performs the before/after filtering counting
    read_pairs_before = {} # The counting is performed in pairs since my files come from only two donors
    read_pairs_after = {}
    for i in range(0, len(read_files), 2):
        donor_id = (i // 2) // 2 + 1  # This will just adjust per donor 1 or 2
        key = f"Donor {donor_id}"
        before, after = run_bowtie2_and_count_reads(read_files[i], read_files[i + 1], index_prefix)
        if key in read_pairs_before:
            read_pairs_before[key] += before
            read_pairs_after[key] += after
        else:
            read_pairs_before[key] = before
            read_pairs_after[key] = after
    return read_pairs_before, read_pairs_after

def write_to_log(filename, read_pairs_before, read_pairs_after): # Later, the output log file will be defined so this will just make sure to write the answer as instructed in there
    with open(filename, "w") as log_file:
        for key in sorted(read_pairs_before.keys()):
            log_file.write(f"{key} had {read_pairs_before[key]} read pairs before Bowtie2 filtering and {read_pairs_after[key]} read pairs after.\n")

# To solve PART 3, ASSEMBLING THE 4 TRANSCRIPTOMES AND WRITING THE COMMAND-LINE USED *Rest of the functions later in the code
def write_spades_command_to_log(filename, spades_cmd): # Writes the command-line used to run the assembly by SPAdes
    with open(filename, "a") as log_file:
        log_file.write("SPAdes command: " + " ".join(spades_cmd) + "\n")

# To solve PART 4, CALCULATING NUMBER OF CONTIGS
def calculate_contig_stats(assembly_file): # To calculate the number of contigs that are longer than 1000 base pairs and the total of base pairs contained within the contigs from the assembly file
    num_contigs_over_1000bp = 0 # To initialize the variables to 0. Ready for counting!
    total_bp_over_1000bp = 0

    with open(assembly_file, 'r') as assembly: # To open the assembly file in read mode
        for line in assembly: # To iterate over each line in the assembly 
            if line.startswith('>'): # To identify the header of a fasta file which starts with a >
                header = line.strip().split('_') # To split whitespace
                try:
                    length_index = header.index('length') # This will look for the index of the substring to figure out the length of the contig
                    length = int(header[length_index + 1]) # The formula of the above
                    if length > 1000: # If the contig length if over 1000 bp it will count it 
                        num_contigs_over_1000bp += 1  
                        total_bp_over_1000bp += length # The count will be added here
                except ValueError:
                    print("Error: Unable to extract length from header line:", line.strip())
                except IndexError:
                    print("Error: Index out of range in header line:", line.strip())

    return num_contigs_over_1000bp, total_bp_over_1000bp

def retrieve_longest_contig(assembly_file, output_file): # This will identify the longest contig from the assembly file and save it to a different file
    longest_contig_name = "" # To store the header line of the longest contig found
    longest_contig_length = 0 # To store the length of it

    with open(assembly_file, 'r') as assembly: # To open the file I name later as ASSEMBLY where the assemby will be written
        for line in assembly: # The rest chunk of code is similar to before when counting contigs
            if line.startswith('>'):
                header = line.strip().split('_')
                try:
                    length_index = header.index('length')
                    length = int(header[length_index + 1])
                    if length > longest_contig_length:
                        longest_contig_length = length
                        longest_contig_name = line.strip()
                except ValueError:
                    print("Error: Unable to extract length from header line:", line.strip())
                except IndexError:
                    print("Error: Index out of range in header line:", line.strip())

    with open(assembly_file, 'r') as assembly:
        with open(output_file, 'w') as output:
            for line in assembly:
                if line.strip() == longest_contig_name:
                    output.write(line)
                    for line in assembly:
                        if line.startswith('>'):
                            break
                        output.write(line)
                    break
# To solve PART 5, RETRIEVE LONGEST CONTIG, BLAST+ AGAINST HERPES SUBFAMILY DATABASE, OUTPUT BEST ALIGNMENT 10 HITS WITH HEADER ROW
def perform_blast():
    query_file = "LONGEST_CONTIG" # This will define the retrieved longest contig from the SPAdes assembly
    database_name = "betaherpesvirinae" # This will define the database so we can Blast against it *More instructions on how to do it in my repo
    log_file = "PipelineProject.log" # Tho define where all answers will be written to

    blast_cmd = [ # To define the Blast+ command
        "blastn",  # Chose blastn since nucleotide-nucleotide are being compared
        "-query", query_file,  # Query already defined as the longest contig
        "-db", database_name,  # Database already defined as betaherpesvirinae (subfamily)
        "-outfmt", "6 sacc pident length qstart qend sstart send bitscore evalue stitle",  # Output format
        "-max_target_seqs", "10",  # The number of hits wanted
        "-max_hsps", "1"  # To keep only the best alignment, high scoring pairs
    ]

    try:
        result = subprocess.run(blast_cmd, capture_output=True, text=True, check=True) # To run BLAST+

        with open(log_file, "a") as f:
            f.write("sacc\tpident\tlength\tqstart\tqend\tsstart\tsend\tbitscore\tevalue\tstitle\n") # To write the header row as wanted
            f.write(result.stdout) # To write the top hits only
    except subprocess.CalledProcessError as e:
        print(f"Error running Blast+: {e}")
        return

if __name__ == "__main__":
    if len(sys.argv) < 10:
        print("Usage: python script.py <index> <read1_1> <read1_2> <read2_1> <read2_2> <read3_1> <read3_2> <read4_1> <read4_2>") # The command-line expected to run this python wrapper
        sys.exit(1)

    index_prefix = sys.argv[1] # So the code assumes that the first word in the command-line is the script itself
    read_files = sys.argv[2:] # This will assume the rest are the index and then sample files to use
    
    read_pairs_before, read_pairs_after = process_paired_end_reads(read_files, index_prefix) # To process the read files with the actual Bowtie2 filtering
    
    log_filename = "PipelineProject.log"
    
    write_to_log(log_filename, read_pairs_before, read_pairs_after)
   # The SPAdes assembly of PART 3  
    spades_output_dir = "ASSEMBLY" # To write the SPAdes command to the log file *pe1/2/3.. are just regular uses for a SPAdes command
    spades_cmd = [
        "spades.py",
        "-o", spades_output_dir,
        "--pe1-1", read_files[0],
        "--pe1-2", read_files[1],
        "--pe2-1", read_files[2],
        "--pe2-2", read_files[3],
        "--pe3-1", read_files[4],
        "--pe3-2", read_files[5],
        "--pe4-1", read_files[6],
        "--pe4-2", read_files[7]
    ]
    write_spades_command_to_log(log_filename, spades_cmd) # To write the SPAdes command used as instructed
    
    num_contigs_over_1000bp, total_bp_over_1000bp = calculate_contig_stats(os.path.join(spades_output_dir, "contigs.fasta")) # To calculate the contigs
    
    with open(log_filename, "a") as log_file: # To write the contig statistics to the log file
        log_file.write(f"There are {num_contigs_over_1000bp} contigs > 1000 bp in the assembly.\n")
        log_file.write(f"There are {total_bp_over_1000bp} bp in the assembly.\n")
    
    longest_contig_file = "LONGEST_CONTIG" # To retrieve and save the longest contig
    retrieve_longest_contig(os.path.join(spades_output_dir, "contigs.fasta"), longest_contig_file)

    perform_blast() # To BLAST

    # Just to print messages of success...
    print(f"Bowtie2 counts before/after filtering written to {log_filename}.")
    print(f"SPAdes assembly completed. Command-line written to {log_filename}.")
    print(f"Assembly contigs written to {log_filename}")
    print(f"Longest contig saved in {longest_contig_file}.")
    print(f"Pipeline complete! See {log_filename}.")