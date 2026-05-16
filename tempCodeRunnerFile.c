#include <stdio.h>

struct SinhVien {
    int maso;
    float dtb;
};

int main() {

    int n, dem = 0;
    float tong = 0;

    printf("Nhap so hoc sinh: ");
    scanf("%d",&n);

    struct SinhVien sv[n];

    // Nhap du lieu
    for(int i = 0; i < n; i++)
    {
        printf("Nhap ma so: ");
        scanf("%d",&sv[i].maso);

        printf("Nhap diem TB: ");
        scanf("%f",&sv[i].dtb);
    }

    // Sap xep tang dan theo diem
    for(int i = 0; i < n-1; i++)
        for(int j = i+1; j < n; j++)
            if(sv[i].dtb > sv[j].dtb)
            {
                struct SinhVien t = sv[i];
                sv[i] = sv[j];
                sv[j] = t;
            }

    printf("\nDanh sach hoc sinh :\n");
    printf("+----------------------+----------+\n"); 
    printf("| %-20s | %-8s |\n","Ma So","Diem TB"); 
    printf("+----------------------+----------+\n"); 
    for(int i = 0; i < n; i++) 
    { 
        printf("| %-20d | %-8.2f |\n", sv[i].maso, sv[i].dtb); 
    } 
    printf("+----------------------+----------+\n");
    // Dem SV DTB > 7
    for(int i = 0; i < n; i++)
    {
        if(sv[i].dtb > 7) dem++;
        tong += sv[i].dtb;
    }

    printf("\nSo hoc sinh DTB > 7: %d\n",dem);
    printf("DTB ca lop: %.2f\n",tong/n);

    return 0;
}