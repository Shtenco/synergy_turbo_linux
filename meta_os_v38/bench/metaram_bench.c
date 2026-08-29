#define _POSIX_C_SOURCE 200809L
#include "metaram.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);return (uint64_t)t.tv_sec*1000000000ull+(uint64_t)t.tv_nsec;}
static void mutate(uint8_t*p,size_t page_id,unsigned gen){if((page_id+gen)%3==0){size_t pos=((page_id*131u)+gen*17u)%MR_PAGE_SIZE;for(size_t i=0;i<16;++i)p[(pos+i)%MR_PAGE_SIZE]^=(uint8_t)(gen+i+1);}}
int main(int argc,char**argv){
 if(argc!=2){fprintf(stderr,"usage: %s input.bin\n",argv[0]);return 2;}
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;fseek(f,0,SEEK_END);long sz=ftell(f);rewind(f);if(sz<=0)return 2;
 size_t pages=((size_t)sz+MR_PAGE_SIZE-1)/MR_PAGE_SIZE;uint8_t*src=calloc(pages,MR_PAGE_SIZE);uint8_t*prev=calloc(pages,MR_PAGE_SIZE);uint8_t*out=calloc(1,MR_PAGE_SIZE);mr_page_blob*blobs=calloc(pages,sizeof(*blobs));
 if(!src||!prev||!out||!blobs)return 2;fread(src,1,(size_t)sz,f);fclose(f);memcpy(prev,src,pages*MR_PAGE_SIZE);
 const unsigned gens=4;uint64_t logical=0,stored=0,en=0,de=0,cc[6]={0};
 for(unsigned g=0;g<gens;++g){if(g)for(size_t p=0;p<pages;++p)mutate(src+p*MR_PAGE_SIZE,p,g);for(size_t p=0;p<pages;++p){const uint8_t*old=g?prev+p*MR_PAGE_SIZE:NULL;int hot=((p+g)%5==0);uint64_t t=ns();if(mr_compress_page(src+p*MR_PAGE_SIZE,old,p,g,1800000000000000000ull+g*1000000ull+p,hot,&blobs[p]))return 3;en+=ns()-t;logical+=MR_PAGE_SIZE;stored+=blobs[p].meta.stored_bytes+sizeof(mr_page_meta);if(blobs[p].meta.codec<6)cc[blobs[p].meta.codec]++;t=ns();if(mr_decompress_page(&blobs[p],old,out))return 4;de+=ns()-t;if(memcmp(out,src+p*MR_PAGE_SIZE,MR_PAGE_SIZE))return 5;}memcpy(prev,src,pages*MR_PAGE_SIZE);}
 double mib=(double)logical/(1024.0*1024.0);printf("{\n  \"pages\": %zu,\n  \"generations\": %u,\n  \"logical_bytes\": %"PRIu64",\n  \"physical_bytes_with_meta\": %"PRIu64",\n  \"effective_ratio\": %.6f,\n  \"encode_mib_s\": %.3f,\n  \"decode_mib_s\": %.3f,\n  \"codec_counts\": {\"RAW\": %"PRIu64", \"ZERO\": %"PRIu64", \"FILL\": %"PRIu64", \"LZ4\": %"PRIu64", \"XOR_LZ4\": %"PRIu64", \"SAME_PREV\": %"PRIu64"}\n}\n",pages,gens,logical,stored,(double)logical/stored,mib/((double)en/1e9),mib/((double)de/1e9),cc[0],cc[1],cc[2],cc[3],cc[4],cc[5]);
 free(src);free(prev);free(out);free(blobs);return 0;}
