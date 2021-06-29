#include <stdlib.h>
#include <stdio.h>
#include <string.h>

//include the printer header file...
#include "printer.h"

#define total 5 // total documents

int main(int argc, char** argv){
    //create a new printer doc...
    doc printer_docs[total];
    get_queued_docs(total, printer_docs);
    print_queued_docs(total, printer_docs);
    return 0; // for success
}

//initialize the list with docs
void get_queued_docs(int size, doc* printer_docs){
    char title[20];
    for(int i = 0; i < size; i++){
        snprintf(title, 20, "doc_%d", i);
        doc new_doc; //define new doc
        new_doc.id = i;
        strcpy(new_doc.title, title);
        printer_docs[i] = new_doc;
    }
} 

//prints out that doc...
void print_queued_docs(int size, doc* printer_docs){
    printf("Items to print:\nPrinter Id  |  Doc title \n");
    for(int i = 0; i < size; i++){
        doc document = printer_docs[i];
        printf("     %d      |  %s   \n", document.id, document.title);
    }
} 